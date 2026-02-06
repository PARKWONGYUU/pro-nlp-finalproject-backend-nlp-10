import re
import onnxruntime as ort
import pickle
from pathlib import Path
from typing import Optional, Dict, Tuple
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# S3 파일명 패턴  (예: 60d_20260206.onnx, 60d_preprocessing_20260206.pkl)
_ONNX_PATTERN = re.compile(r"60d_(\d{8})\.onnx$")
_PKL_PATTERN = re.compile(r"60d_preprocessing_(\d{8})\.pkl$")


class ONNXModelLoader:
    """
    ONNX 모델 로더

    두 가지 모드 지원:
    - local : LOCAL_MODEL_PATH 폴더에서 *.onnx / *.pkl 직접 로드
    - s3   : S3 prefix 아래에서 날짜(YYYYMMDD) 기준 최신 파일을 찾아 다운로드
              ETag 기반으로 변경 감지 → 자동 리로드

    S3 키 예시:
      s3://aitech-storage/models/enhanced_tft/champion/60d_20260206.onnx
      s3://aitech-storage/models/enhanced_tft/champion/60d_preprocessing_20260206.pkl
    """

    def __init__(self):
        self.mode = settings.model_load_mode
        self.local_path = Path(settings.local_model_path)

        # 캐시 -----------------------------------------------------------------
        self.sessions: Dict[str, ort.InferenceSession] = {}      # {commodity: session}
        self.preprocessing_info: Dict[str, dict] = {}             # {commodity: pkl_data}
        self._loaded_keys: Dict[str, Dict[str, str]] = {}         # {commodity: {"onnx_key":..., "pkl_key":...}}
        self._etags: Dict[str, Dict[str, str]] = {}               # {commodity: {"model": etag, "pkl": etag}}

        # S3 클라이언트 (lazy init)
        self._s3_client = None
        # 로컬 캐시 디렉토리 (S3 다운로드용)
        self._cache_dir = Path("./models_cache")

        logger.info(f"모델 로더 초기화: mode={self.mode}, path={self.local_path}")

    # ===========================================
    # Public API
    # ===========================================

    def load_session(self, commodity: str = "corn") -> ort.InferenceSession:
        """
        ONNX 세션 로드 (캐싱)

        - local 모드: temp/ 폴더에서 파일을 찾아 로드
        - s3 모드  : S3 prefix 아래 최신 파일을 다운로드 후 로드
        """
        if self.mode == "local":
            return self._load_local(commodity)
        return self._load_from_s3(commodity)

    def get_preprocessing_info(self, commodity: str = "corn") -> dict:
        """전처리 정보(pkl) 반환. 세션이 없으면 먼저 로드."""
        if commodity not in self.sessions:
            self.load_session(commodity)
        return self.preprocessing_info.get(commodity, {})

    def check_and_update(self, commodity: str = "corn") -> bool:
        """
        S3에 새 모델이 올라왔는지 확인 → 변경됐으면 리로드.

        Returns:
            True = 모델 갱신됨, False = 변경 없음
        """
        if self.mode != "s3":
            logger.debug("로컬 모드에서는 자동 업데이트를 건너뜁니다.")
            return False

        s3 = self._get_s3_client()
        bucket = settings.model_s3_bucket

        # 최신 파일 키 조회
        latest_onnx_key, latest_pkl_key = self._find_latest_s3_keys(s3, bucket)
        if not latest_onnx_key:
            logger.warning("S3에서 ONNX 파일을 찾을 수 없습니다.")
            return False

        # 현재 로드된 키와 비교
        loaded = self._loaded_keys.get(commodity, {})
        if loaded.get("onnx_key") == latest_onnx_key:
            logger.info(f"[{commodity}] 모델 변경 없음: {latest_onnx_key}")
            return False

        logger.info(
            f"[{commodity}] 새 모델 감지! "
            f"({loaded.get('onnx_key', 'None')} → {latest_onnx_key})"
        )

        # 기존 세션 제거 후 재로드
        self.sessions.pop(commodity, None)
        self.preprocessing_info.pop(commodity, None)
        self._etags.pop(commodity, None)
        self._loaded_keys.pop(commodity, None)
        self._load_from_s3(commodity)
        return True

    # ===========================================
    # Local 모드
    # ===========================================

    def _load_local(self, commodity: str) -> ort.InferenceSession:
        """로컬 파일에서 모델 로드"""
        if commodity in self.sessions:
            return self.sessions[commodity]

        onnx_file, pkl_file = self._find_local_files()

        logger.info(f"ONNX 세션 생성 중... {onnx_file.name}")
        session = ort.InferenceSession(
            str(onnx_file), providers=["CPUExecutionProvider"]
        )
        self.sessions[commodity] = session
        logger.info(f"✅ ONNX 세션 생성 완료: {onnx_file.name}")

        if pkl_file and pkl_file.exists():
            with open(pkl_file, "rb") as f:
                self.preprocessing_info[commodity] = pickle.load(f)
            logger.info(f"✅ 전처리 정보 로드 완료: {pkl_file.name}")
        else:
            logger.warning("⚠️ 전처리 정보 파일이 없습니다")

        return session

    def _find_local_files(self) -> Tuple[Path, Optional[Path]]:
        """로컬 경로에서 ONNX, PKL 파일 찾기 (파일명 정렬 → 마지막 = 최신)"""
        onnx_files = sorted(self.local_path.glob("*.onnx"))
        pkl_files = sorted(self.local_path.glob("*.pkl"))

        if not onnx_files:
            raise FileNotFoundError(
                f"ONNX 모델 파일을 찾을 수 없습니다: {self.local_path}"
            )

        onnx_file = onnx_files[-1]
        pkl_file = pkl_files[-1] if pkl_files else None

        logger.info(f"로컬 모델 파일 발견: {onnx_file.name}")
        if pkl_file:
            logger.info(f"전처리 정보 파일 발견: {pkl_file.name}")

        return onnx_file, pkl_file

    # ===========================================
    # S3 모드
    # ===========================================

    def _load_from_s3(self, commodity: str) -> ort.InferenceSession:
        """S3에서 최신 모델을 다운로드하고 세션 생성"""
        if commodity in self.sessions:
            return self.sessions[commodity]

        s3 = self._get_s3_client()
        bucket = settings.model_s3_bucket

        cache_dir = self._cache_dir / commodity
        cache_dir.mkdir(parents=True, exist_ok=True)

        # S3에서 최신 파일 키 찾기
        latest_onnx_key, latest_pkl_key = self._find_latest_s3_keys(s3, bucket)

        if not latest_onnx_key:
            raise FileNotFoundError(
                f"S3에서 ONNX 모델 파일을 찾을 수 없습니다: "
                f"s3://{bucket}/{settings.model_s3_prefix}/"
            )

        # --- ONNX 다운로드 ---
        model_local = cache_dir / "model.onnx"
        model_etag = self._download_if_changed(
            s3, bucket, latest_onnx_key, model_local,
            self._etags.get(commodity, {}).get("model"),
        )

        # --- PKL 다운로드 ---
        pkl_local = cache_dir / "preprocessing.pkl"
        pkl_etag = None
        if latest_pkl_key:
            pkl_etag = self._download_if_changed(
                s3, bucket, latest_pkl_key, pkl_local,
                self._etags.get(commodity, {}).get("pkl"),
            )

        # 캐시 업데이트
        self._etags[commodity] = {"model": model_etag, "pkl": pkl_etag}
        self._loaded_keys[commodity] = {
            "onnx_key": latest_onnx_key,
            "pkl_key": latest_pkl_key,
        }

        # ONNX 세션 생성
        logger.info(f"[{commodity}] ONNX 세션 생성 중...")
        session = ort.InferenceSession(
            str(model_local), providers=["CPUExecutionProvider"]
        )
        self.sessions[commodity] = session
        logger.info(f"✅ [{commodity}] ONNX 세션 생성 완료 (from {latest_onnx_key})")

        # 전처리 정보 로드
        if pkl_local.exists() and pkl_local.stat().st_size > 0:
            with open(pkl_local, "rb") as f:
                self.preprocessing_info[commodity] = pickle.load(f)
            logger.info(f"✅ [{commodity}] 전처리 정보 로드 완료 (from {latest_pkl_key})")
        else:
            logger.warning(f"⚠️ [{commodity}] 전처리 정보 파일이 없습니다")

        return session

    def _find_latest_s3_keys(
        self, s3, bucket: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        S3 prefix 아래 파일 목록을 조회하여 날짜(YYYYMMDD)가 가장 큰
        ONNX / PKL 파일 키를 반환.

        Returns:
            (latest_onnx_key, latest_pkl_key)  — 없으면 None
        """
        prefix = settings.model_s3_prefix.rstrip("/") + "/"

        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

        onnx_candidates: list[Tuple[str, str]] = []  # (date_str, key)
        pkl_candidates: list[Tuple[str, str]] = []

        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                filename = key.rsplit("/", 1)[-1]

                m_onnx = _ONNX_PATTERN.search(filename)
                if m_onnx:
                    onnx_candidates.append((m_onnx.group(1), key))
                    continue

                m_pkl = _PKL_PATTERN.search(filename)
                if m_pkl:
                    pkl_candidates.append((m_pkl.group(1), key))

        latest_onnx = max(onnx_candidates, key=lambda x: x[0])[1] if onnx_candidates else None
        latest_pkl = max(pkl_candidates, key=lambda x: x[0])[1] if pkl_candidates else None

        if latest_onnx:
            logger.info(f"S3 최신 ONNX: {latest_onnx}")
        if latest_pkl:
            logger.info(f"S3 최신 PKL:  {latest_pkl}")

        return latest_onnx, latest_pkl

    def _download_if_changed(
        self, s3, bucket: str, key: str, local_path: Path, cached_etag: Optional[str]
    ) -> Optional[str]:
        """
        S3 오브젝트를 ETag 비교 후 변경됐을 때만 다운로드.

        Returns:
            새 ETag, 또는 None (파일이 S3에 없을 때)
        """
        try:
            head = s3.head_object(Bucket=bucket, Key=key)
            remote_etag = head["ETag"]
        except Exception as e:
            logger.warning(f"S3 HEAD 실패: s3://{bucket}/{key} → {e}")
            return None

        if cached_etag == remote_etag and local_path.exists():
            logger.debug(f"캐시 유효 (ETag 동일): {key}")
            return remote_etag

        logger.info(f"S3 다운로드: s3://{bucket}/{key} → {local_path}")
        s3.download_file(bucket, key, str(local_path))
        logger.info(f"✅ 다운로드 완료: {local_path.name} ({head['ContentLength']} bytes)")

        return remote_etag

    def _get_s3_client(self):
        """boto3 S3 클라이언트 (lazy init)"""
        if self._s3_client is None:
            import boto3

            self._s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region,
            )
            logger.info(
                f"S3 클라이언트 초기화: region={settings.aws_region}, "
                f"bucket={settings.model_s3_bucket}"
            )

        return self._s3_client


# ===========================================
# 싱글톤 & 스케줄러
# ===========================================

_model_loader: Optional[ONNXModelLoader] = None


def get_model_loader() -> ONNXModelLoader:
    """모델 로더 싱글톤 반환"""
    global _model_loader
    if _model_loader is None:
        _model_loader = ONNXModelLoader()
    return _model_loader


def start_model_update_scheduler():
    """
    모델 자동 업데이트 스케줄러 시작

    S3 모드에서만 동작.
    MODEL_UPDATE_CHECK_TIME 에 따라 매일 지정 시각에 S3를 확인하고,
    새 파일(날짜 suffix가 더 큰 파일)이 있으면 자동 리로드.
    """
    if settings.model_load_mode != "s3":
        logger.info("로컬 모드 → 모델 업데이트 스케줄러를 건너뜁니다.")
        return None

    from apscheduler.schedulers.background import BackgroundScheduler

    hour, minute = map(int, settings.model_update_check_time.split(":"))

    scheduler = BackgroundScheduler()

    def _check_update_job():
        logger.info("⏰ 스케줄러: 모델 업데이트 확인 중...")
        loader = get_model_loader()
        updated = loader.check_and_update("corn")
        if updated:
            logger.info("🔄 모델이 갱신되었습니다.")
        else:
            logger.info("✅ 모델 변경 없음.")

    scheduler.add_job(
        _check_update_job,
        trigger="cron",
        hour=hour,
        minute=minute,
        id="model_update_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"📅 모델 업데이트 스케줄러 시작: 매일 {settings.model_update_check_time}")

    return scheduler

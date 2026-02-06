from pydantic_settings import BaseSettings
from pydantic import field_validator, ValidationInfo
from typing import List, Optional
import re


class Settings(BaseSettings):
    """
    애플리케이션 설정 관리
    
    환경 변수(.env 파일)에서 설정을 로드합니다.
    """
    
    # ===========================
    # 데이터베이스 설정
    # ===========================
    database_url: str
    
    # ===========================
    # 모델 로딩 설정
    # ===========================
    model_load_mode: str = "local"  # "local" 또는 "s3"
    local_model_path: str = "./temp"
    
    @field_validator('model_load_mode')
    @classmethod
    def validate_model_load_mode(cls, v: str) -> str:
        """모델 로딩 모드 검증"""
        allowed_modes = {'local', 's3'}
        if v.lower() not in allowed_modes:
            raise ValueError(
                f"model_load_mode는 'local' 또는 's3'이어야 합니다. 입력값: {v}"
            )
        return v.lower()
    
    # ===========================
    # AWS S3 설정 (선택 사항)
    # ===========================
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "ap-northeast-2"
    model_s3_bucket: Optional[str] = None
    
    @field_validator('model_s3_bucket')
    @classmethod
    def validate_s3_config(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """S3 모드일 때 필수 설정 검증"""
        if info.data.get('model_load_mode') == 's3':
            if not v:
                raise ValueError(
                    "model_load_mode가 's3'일 때 model_s3_bucket은 필수입니다."
                )
            if not info.data.get('aws_access_key_id') or not info.data.get('aws_secret_access_key'):
                raise ValueError(
                    "model_load_mode가 's3'일 때 AWS 자격증명(aws_access_key_id, aws_secret_access_key)은 필수입니다."
                )
        return v
    
    # ===========================
    # 모델 업데이트 설정
    # ===========================
    model_update_check_time: str = "03:00"
    
    @field_validator('model_update_check_time')
    @classmethod
    def validate_update_time(cls, v: str) -> str:
        """모델 업데이트 시간 형식 검증 (HH:MM)"""
        pattern = re.compile(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$')
        if not pattern.match(v):
            raise ValueError(
                f"model_update_check_time은 'HH:MM' 형식이어야 합니다 (예: '03:00'). 입력값: {v}"
            )
        return v
    
    # ===========================
    # Feature 설정
    # ===========================
    adjustable_features: List[str] = [
        "US_10Y_YIELD",      # 미국 10년물 국채 금리
        "DXY",               # 달러 인덱스
        "PDSI",              # Palmer Drought Severity Index
        "SPI_30D",           # Standardized Precipitation Index (30일)
        "SPI_90D"            # Standardized Precipitation Index (90일)
    ]
    
    # ===========================
    # 시계열 설정
    # ===========================
    encoder_length: int = 60  # 과거 시계열 길이
    prediction_length: int = 7  # 미래 예측 길이
    
    @field_validator('encoder_length', 'prediction_length')
    @classmethod
    def validate_positive(cls, v: int) -> int:
        """양수 검증"""
        if v <= 0:
            raise ValueError(f"값은 양수여야 합니다. 입력값: {v}")
        return v
    
    # ===========================
    # 기타 설정
    # ===========================
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 추가 필드 무시


# 전역 설정 인스턴스
settings = Settings()


def get_settings() -> Settings:
    """설정 인스턴스 반환"""
    return settings


# 설정 정보 출력 (디버깅용)
def print_settings_info():
    """현재 설정 정보 출력"""
    print("=" * 60)
    print("현재 애플리케이션 설정")
    print("=" * 60)
    print(f"모델 로딩 모드: {settings.model_load_mode}")
    print(f"로컬 모델 경로: {settings.local_model_path}")
    
    if settings.model_load_mode == "s3":
        print(f"S3 버킷: {settings.model_s3_bucket}")
        print(f"AWS 리전: {settings.aws_region}")
    
    print(f"모델 업데이트 체크 시간: {settings.model_update_check_time}")
    print(f"Encoder 길이: {settings.encoder_length}")
    print(f"예측 길이: {settings.prediction_length}")
    print(f"조정 가능 Feature 개수: {len(settings.adjustable_features)}")
    print("=" * 60)

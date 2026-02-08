"""
실시간 시장 데이터 수집 모듈

외부 API를 통해 market_metrics에 필요한 데이터를 실시간으로 가져옵니다.
"""

import logging
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


class DataFetcher:
    """실시간 데이터 수집 클래스"""
    
    def __init__(self, fred_api_key: Optional[str] = None):
        """
        초기화
        
        Args:
            fred_api_key: FRED API 키 (선택사항)
        """
        self.fred_api_key = fred_api_key
        self._fred_client = None
        
    def _get_fred_client(self):
        """FRED API 클라이언트 지연 로딩"""
        if self._fred_client is None and self.fred_api_key:
            try:
                from fredapi import Fred
                self._fred_client = Fred(api_key=self.fred_api_key)
                logger.info("FRED API 클라이언트 초기화 완료")
            except ImportError:
                logger.warning("fredapi 패키지가 설치되지 않았습니다. 경제 지표는 더미 데이터로 대체됩니다.")
            except Exception as e:
                logger.warning(f"FRED API 클라이언트 초기화 실패: {e}. 더미 데이터로 대체됩니다.")
        return self._fred_client
    
    def fetch_price_data(self, commodity: str, end_date: date, days: int) -> tuple[pd.DataFrame, bool]:
        """
        yfinance로 가격 데이터 수집
        
        Args:
            commodity: 품목명 (예: "corn", "Corn" 모두 가능)
            end_date: 종료 날짜
            days: 조회할 일수
            
        Returns:
            (가격 데이터프레임, 실제 데이터 여부)
            데이터프레임 columns: date, close, open, high, low, volume
        """
        try:
            import yfinance as yf
            
            # 품목명을 소문자로 통일
            commodity = commodity.lower()
            
            # 품목별 심볼 매핑
            symbol_map = {
                'corn': 'ZC=F',  # 옥수수 선물
                'wheat': 'ZW=F',  # 밀 선물
            }
            
            symbol = symbol_map.get(commodity.lower(), 'ZC=F')
            
            # 넉넉하게 추가 일수를 더해서 다운로드 (휴장일 고려)
            start_date = end_date - timedelta(days=days + 30)
            
            logger.info(f"yfinance로 {symbol} 데이터 다운로드: {start_date} ~ {end_date}")
            
            # 데이터 다운로드
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date + timedelta(days=1))
            
            if df.empty:
                raise ValueError(f"yfinance에서 {symbol} 데이터를 가져올 수 없습니다.")
            
            # 인덱스를 컬럼으로 변환 (날짜가 인덱스에 있음)
            df = df.reset_index()
            
            # 컬럼명 소문자로 변경
            df.columns = [col.lower() for col in df.columns]
            
            # 'date' 컬럼 처리
            if 'date' not in df.columns:
                # 인덱스가 날짜인 경우 첫 번째 컬럼이 날짜
                df.rename(columns={df.columns[0]: 'date'}, inplace=True)
            
            df['date'] = pd.to_datetime(df['date']).dt.date
            
            # 필요한 컬럼만 선택
            df = df[['date', 'close', 'open', 'high', 'low', 'volume']]
            
            # 최근 N일만 선택
            df = df.tail(days)
            
            logger.info(f"가격 데이터 수집 완료: {len(df)}일 (실제 데이터)")
            
            return df, True  # 실제 yfinance 데이터
            
        except ImportError:
            logger.error("yfinance 패키지가 설치되지 않았습니다.")
            raise
        except Exception as e:
            logger.error(f"가격 데이터 수집 실패: {e}")
            # 폴백: 더미 데이터 생성
            return self._generate_dummy_price_data(end_date, days), False
    
    def fetch_economic_data(self, end_date: date, days: int) -> tuple[pd.DataFrame, bool]:
        """
        FRED API로 경제 지표 수집
        
        Args:
            end_date: 종료 날짜
            days: 조회할 일수
            
        Returns:
            (경제 지표 데이터프레임, 실제 데이터 여부)
            데이터프레임 columns: date, 10Y_Yield, USD_Index
        """
        fred = self._get_fred_client()
        
        if not fred:
            logger.warning("FRED API 사용 불가. 더미 데이터로 대체합니다.")
            return self._generate_dummy_economic_data(end_date, days), False
        
        try:
            start_date = end_date - timedelta(days=days + 30)
            
            logger.info(f"FRED API로 경제 지표 다운로드: {start_date} ~ {end_date}")
            
            # 10년물 국채 금리
            treasury_10y = fred.get_series('DGS10', start_date, end_date)
            
            # 달러 인덱스 (구 심볼이 deprecated되어 새로운 심볼 사용)
            try:
                usd_index = fred.get_series('DTWEXBGS', start_date, end_date)
            except:
                # 새로운 심볼로 시도
                usd_index = fred.get_series('DTWEXEMEGS', start_date, end_date)
            
            # 데이터프레임 생성
            df = pd.DataFrame({
                '10Y_Yield': treasury_10y,
                'USD_Index': usd_index
            })
            
            df = df.reset_index()
            df.columns = ['date', '10Y_Yield', 'USD_Index']
            df['date'] = pd.to_datetime(df['date']).dt.date
            
            # 결측치 처리 (forward fill)
            df = df.fillna(method='ffill').fillna(method='bfill')
            
            # 최근 N일만 선택
            df = df.tail(days)
            
            logger.info(f"경제 지표 수집 완료: {len(df)}일 (실제 데이터)")
            
            return df, True  # 실제 FRED 데이터
            
        except Exception as e:
            logger.error(f"FRED API 데이터 수집 실패: {e}")
            return self._generate_dummy_economic_data(end_date, days), False
    
    def _generate_dummy_price_data(self, end_date: date, days: int) -> pd.DataFrame:
        """더미 가격 데이터 생성"""
        logger.warning(f"더미 가격 데이터 생성 ({days}일)")
        
        dates = [end_date - timedelta(days=days-1-i) for i in range(days)]
        
        # 현실적인 옥수수 가격 범위 (센트/부셸)
        base_price = 450.0
        prices = []
        current_price = base_price
        
        for _ in range(days):
            # 작은 랜덤 변화
            change = np.random.normal(0, 5)
            current_price = max(400, min(500, current_price + change))
            prices.append(current_price)
        
        df = pd.DataFrame({
            'date': dates,
            'close': prices,
            'open': [p + np.random.uniform(-2, 2) for p in prices],
            'high': [p + np.random.uniform(2, 5) for p in prices],
            'low': [p - np.random.uniform(2, 5) for p in prices],
            'volume': [np.random.randint(50000, 150000) for _ in range(days)]
        })
        
        return df
    
    def _generate_dummy_economic_data(self, end_date: date, days: int) -> pd.DataFrame:
        """더미 경제 지표 데이터 생성"""
        logger.warning(f"더미 경제 지표 데이터 생성 ({days}일)")
        
        dates = [end_date - timedelta(days=days-1-i) for i in range(days)]
        
        df = pd.DataFrame({
            'date': dates,
            '10Y_Yield': np.random.uniform(3.5, 4.5, days),  # 3.5% ~ 4.5%
            'USD_Index': np.random.uniform(100, 110, days)   # 100 ~ 110
        })
        
        return df
    
    def generate_dummy_features(self, days: int) -> Dict[str, List[float]]:
        """
        더미 feature 데이터 생성
        
        뉴스 PCA, 기후 지수, Hawkes intensity 등을 생성합니다.
        
        Args:
            days: 조회할 일수
            
        Returns:
            feature별 시계열 데이터
        """
        features = {}
        
        # 뉴스 PCA (32개) - 정규분포
        for i in range(32):
            # 시계열 연속성을 위해 랜덤워크 방식
            values = []
            current = np.random.normal(0, 1)
            for _ in range(days):
                current += np.random.normal(0, 0.1)  # 작은 변화
                values.append(current)
            features[f'news_pca_{i}'] = values
        
        # 기후 지수
        features['pdsi'] = list(np.random.uniform(-3, 3, days))  # -6~6 범위, 중간값 사용
        features['spi30d'] = list(np.random.uniform(-1, 1, days))  # -3~3 범위, 중간값 사용
        features['spi90d'] = list(np.random.uniform(-1, 1, days))
        
        # Hawkes Intensity
        features['lambda_price'] = list(np.random.uniform(0.1, 0.5, days))
        features['lambda_news'] = list(np.random.uniform(0.1, 0.5, days))
        
        # 뉴스 카운트
        features['news_count'] = list(np.random.randint(5, 15, days).astype(float))
        
        return features
    
    def build_features_dict(
        self, 
        commodity: str,
        end_date: date, 
        days: int
    ) -> Dict[str, any]:
        """
        모든 데이터를 수집하여 52개 feature 형식으로 변환
        
        Args:
            commodity: 품목명
            end_date: 종료 날짜
            days: 조회할 일수
            
        Returns:
            {
                'dates': [date1, date2, ...],
                'features': {
                    'close': [v1, v2, ...],
                    'open': [v1, v2, ...],
                    ...
                },
                'is_real_data': bool  # 실제 API 데이터 여부
            }
        """
        logger.info(f"실시간 데이터 수집 시작: {commodity}, {end_date}, {days}일")
        
        # 1. 가격 데이터
        price_df, is_real_price_data = self.fetch_price_data(commodity, end_date, days)
        
        # 2. 경제 지표
        econ_df, is_real_econ_data = self.fetch_economic_data(end_date, days)
        
        # 3. 날짜 정렬 및 병합
        # 가격 데이터의 날짜를 기준으로 사용
        dates = price_df['date'].tolist()
        
        # 경제 지표를 가격 날짜에 맞춰 매핑 (forward fill)
        econ_dict = econ_df.set_index('date').to_dict('index')
        
        features = {}
        
        # 🔥 수정: 로그 변환은 prediction_service에서 수행하도록 변경
        # 여기서는 원본 값(Raw Value)을 반환해야 market_metrics API에서 정상적으로 사용 가능
        
        # 가격/거래량 feature (6개) - 원본 값 사용
        features['close'] = price_df['close'].tolist()
        features['open'] = price_df['open'].tolist()
        features['high'] = price_df['high'].tolist()
        features['low'] = price_df['low'].tolist()
        features['volume'] = price_df['volume'].tolist()
        
        # EMA 계산 - 원본 값으로 계산 (필요시 prediction_service에서 다시 계산)
        features['EMA'] = price_df['close'].ewm(span=20, adjust=False).mean().tolist()
        
        # 경제 지표 (2개) - 날짜 매칭
        features['10Y_Yield'] = []
        features['USD_Index'] = []
        
        last_10y = 4.0  # 기본값
        last_usd = 105.0  # 기본값
        
        for d in dates:
            if d in econ_dict:
                last_10y = econ_dict[d].get('10Y_Yield', last_10y)
                last_usd = econ_dict[d].get('USD_Index', last_usd)
            features['10Y_Yield'].append(last_10y)
            features['USD_Index'].append(last_usd)
        
        # 더미 feature (39개)
        dummy_features = self.generate_dummy_features(len(dates))
        features.update(dummy_features)
        
        # 실제 데이터 여부 결정
        # yfinance만으로도 충분히 실제 데이터로 인정 (API 키 불필요)
        # FRED는 선택사항 (API 키 필요)
        is_real_data = is_real_price_data  # yfinance 데이터만 있으면 OK
        
        logger.info(
            f"실시간 데이터 수집 완료: {len(dates)}일, {len(features)}개 feature"
        )
        logger.info(
            f"데이터 소스: yfinance={'실제' if is_real_price_data else '더미'}, "
            f"FRED={'실제' if is_real_econ_data else '더미'} → "
            f"실제 데이터: {is_real_data}"
        )
        
        return {
            'dates': [str(d) for d in dates],
            'features': features,
            'is_real_data': is_real_data
        }


# 전역 인스턴스 (캐싱용)
_fetcher_instance: Optional[DataFetcher] = None


def get_data_fetcher(fred_api_key: Optional[str] = None) -> DataFetcher:
    """DataFetcher 싱글톤 인스턴스 반환"""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = DataFetcher(fred_api_key=fred_api_key)
    return _fetcher_instance


@lru_cache(maxsize=128)
def fetch_realtime_features_cached(
    commodity: str, 
    end_date_str: str, 
    days: int,
    fred_api_key: Optional[str] = None
) -> str:
    """
    캐싱된 실시간 feature 조회
    
    Note: lru_cache는 hashable 인자만 받으므로 date를 str로 변환
    반환값도 JSON 문자열로 변환하여 캐싱
    """
    import json
    
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    fetcher = get_data_fetcher(fred_api_key)
    result = fetcher.build_features_dict(commodity, end_date, days)
    
    return json.dumps(result)


def fetch_realtime_features(
    commodity: str, 
    end_date: date, 
    days: int,
    fred_api_key: Optional[str] = None
) -> Dict[str, any]:
    """
    실시간 feature 데이터 수집 (캐싱 적용)
    
    Args:
        commodity: 품목명
        end_date: 종료 날짜
        days: 조회할 일수
        fred_api_key: FRED API 키
        
    Returns:
        {
            'dates': [date1, date2, ...],
            'features': {...}
        }
    """
    import json
    
    # 캐싱된 함수 호출
    result_str = fetch_realtime_features_cached(
        commodity, 
        end_date.strftime('%Y-%m-%d'), 
        days,
        fred_api_key
    )
    
    return json.loads(result_str)

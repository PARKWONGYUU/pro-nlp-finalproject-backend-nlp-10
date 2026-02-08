"""
더미 데이터 생성 헬퍼 모듈

시연용으로 말이 되는 더미 데이터를 생성합니다.
실제 데이터가 없을 때만 사용되며, 있는 데이터는 보존됩니다.
"""

import numpy as np
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
import random

from . import dataschemas


class DummyDataGenerator:
    """더미 데이터 생성 클래스"""
    
    # 실제 feature 이름들
    FEATURE_NAMES = [
        'close', 'open', 'high', 'low', 'volume', 'EMA',
        '10Y_Yield', 'USD_Index',
        'pdsi', 'spi30d', 'spi90d',
        'lambda_price', 'lambda_news', 'news_count'
    ] + [f'news_pca_{i}' for i in range(32)]
    
    # 카테고리별 feature 매핑
    FEATURE_CATEGORIES = {
        'Price': ['close', 'open', 'high', 'low', 'EMA'],
        'Macro': ['10Y_Yield', 'USD_Index'],
        'Weather': ['pdsi', 'spi30d', 'spi90d'],
        'Sentiment': [f'news_pca_{i}' for i in range(10)],
        'Liquidity': ['volume'],
        'Demand': [f'news_pca_{i}' for i in range(10, 20)],
        'Quality': [f'news_pca_{i}' for i in range(20, 32)],
    }
    
    def __init__(self, base_price: float = 450.0):
        """
        초기화
        
        Args:
            base_price: 기준 가격 (옥수수 선물 기본값: $450)
        """
        self.base_price = base_price
        self.rng = np.random.default_rng(42)  # 재현성을 위한 시드
    
    def generate_predictions(
        self,
        commodity: str,
        start_date: date,
        days: int = 60,
        trend: float = 0.001
    ) -> List[dataschemas.TftPredResponse]:
        """
        예측 데이터 생성 (현실적인 패턴)
        
        Args:
            commodity: 품목명
            start_date: 시작 날짜
            days: 생성할 일수
            trend: 일일 추세 (0.001 = 0.1% 상승)
        
        Returns:
            TftPredResponse 리스트
        """
        predictions = []
        current_price = self.base_price
        
        # 사이클 설정을 위한 랜덤 위상
        phase_long = self.rng.uniform(0, 2 * np.pi)
        phase_short = self.rng.uniform(0, 2 * np.pi)
        
        for i in range(days):
            target_date = start_date + timedelta(days=i)
            
            # 1. 기본 추세 (Linear Trend)
            trend_component = trend * i
            
            # 2. 장기 사이클 (30일 주기) - 큰 흐름
            cycle_long = 0.02 * np.sin(2 * np.pi * i / 30 + phase_long)
            
            # 3. 단기 사이클 (7일 주기) - 작은 변동
            cycle_short = 0.01 * np.sin(2 * np.pi * i / 7 + phase_short)
            
            # 4. 랜덤 노이즈 (Random Walk)
            noise = self.rng.normal(0, 0.005)
            
            # 가격 계산: 기준가 * (1 + 모든 변동 요인)
            price = self.base_price * (1 + trend_component + cycle_long + cycle_short + noise)
            
            # 신뢰구간: 변동성이 클수록 넓어지게 설정
            # 기본 2% + 사이클 강도에 따른 추가폭
            volatility = 0.02 + 0.01 * abs(np.sin(2 * np.pi * i / 14))
            ci_range = price * volatility
            
            # Top 20 factors 생성
            factors = self._generate_top_factors()
            
            pred = dataschemas.TftPredResponse(
                id=99999 + i,  # 임시 ID
                target_date=target_date,
                commodity=commodity,
                price_pred=round(price, 2),
                conf_lower=round(price - ci_range, 2),
                conf_upper=round(price + ci_range, 2),
                **factors,
                model_type="TFT_DUMMY",
                created_at=datetime.now()
            )
            predictions.append(pred)
        
        return predictions
    
    def _generate_top_factors(self) -> Dict:
        """Top 20 factors 생성"""
        factors = {}
        
        # 실제 feature 이름 사용
        selected_features = self.rng.choice(
            self.FEATURE_NAMES, 
            size=min(20, len(self.FEATURE_NAMES)), 
            replace=False
        )
        
        # Impact는 합이 1이 되도록 정규화
        impacts = self.rng.dirichlet(np.ones(len(selected_features)))
        
        for i, (feature, impact) in enumerate(zip(selected_features, impacts), 1):
            factors[f'top{i}_factor'] = feature
            factors[f'top{i}_impact'] = round(float(impact), 4)
        
        return factors
    
    def generate_explanation(
        self,
        commodity: str,
        target_date: date,
        prediction: Optional[dataschemas.TftPredResponse] = None
    ) -> dataschemas.ExpPredResponse:
        """
        예측 설명 생성
        
        Args:
            commodity: 품목명
            target_date: 목표 날짜
            prediction: 해당 날짜의 예측 (있으면 사용)
        
        Returns:
            ExpPredResponse
        """
        # Executive Summary 템플릿
        if prediction:
            price = prediction.price_pred
            date_str = target_date.strftime('%Y년 %m월 %d일')
        else:
            price = self.base_price
            date_str = target_date.strftime('%Y년 %m월 %d일')
        
        content = f"""
{date_str} {commodity.upper()} 선물 가격 예측 분석

예측 가격: ${price:.2f}

주요 분석 포인트:
• 거시경제 지표: 미국 10년물 국채 금리와 달러 인덱스가 주요 변수로 작용
• 기후 요인: 강수량 지수(SPI)와 가뭄 지수(PDSI)가 중기 전망에 영향
• 시장 심리: 뉴스 감성 분석 결과 중립적 시장 전망
• 유동성: 거래량 지표는 평균 수준 유지

리스크 요인:
- 기상 이변 발생 가능성
- 글로벌 수요 변동성
- 환율 변동 리스크

이 분석은 TFT 모델 기반 예측이며, 실제 시장 상황에 따라 변동될 수 있습니다.
        """.strip()
        
        # Top Factors
        top_factors = self._generate_top_factors_items()
        
        # High Impact News
        impact_news = self._generate_high_impact_news()
        
        # Category Summary
        category_summary = self._generate_category_summary()
        
        return dataschemas.ExpPredResponse(
            id=99999,  # 임시 ID
            pred_id=99999,  # 임시 pred_id
            content=content,
            llm_model="GPT-4-DUMMY",
            impact_news=impact_news,
            top_factors=top_factors,
            category_summary=category_summary,
            created_at=datetime.now()
        )
    
    def _generate_top_factors_items(self, n: int = 10) -> List[dataschemas.TopFactorItem]:
        """Top Factor Items 생성"""
        items = []
        
        # 카테고리별로 고르게 선택
        all_factors = []
        for category, features in self.FEATURE_CATEGORIES.items():
            if features:
                selected = self.rng.choice(features, size=min(2, len(features)), replace=False)
                for feature in selected:
                    all_factors.append((feature, category))
        
        # n개만 선택
        if len(all_factors) > n:
            all_factors = self.rng.choice(all_factors, size=n, replace=False).tolist()
        
        # Impact 생성 (합이 1)
        impacts = self.rng.dirichlet(np.ones(len(all_factors)))
        
        for (feature, category), impact in zip(all_factors, impacts):
            items.append(dataschemas.TopFactorItem(
                name=feature,
                category=category,
                impact=round(float(impact * 100), 2),  # 0~100 범위
                ratio=round(float(impact), 4)  # 0~1 비율
            ))
        
        # Impact 순으로 정렬
        items.sort(key=lambda x: x.impact, reverse=True)
        
        return items
    
    def _generate_high_impact_news(self, n: int = 5) -> List[dataschemas.HighImpactNewsItem]:
        """고영향 뉴스 생성"""
        news_templates = [
            "미 농무부, 올해 옥수수 생산량 {}% {} 전망",
            "중국, 미국산 곡물 수입 {}% {} 발표",
            "가뭄 우려로 주요 산지 작황 {}",
            "달러 강세에 농산물 선물 가격 {}",
            "국제 곡물 재고 {}, 시장 전망 {}",
        ]
        
        items = []
        for i in range(n):
            template = self.rng.choice(news_templates)
            
            # 랜덤 수치 및 방향
            pct = self.rng.integers(2, 15)
            direction = self.rng.choice(['증가', '감소', '상승', '하락', '개선', '악화'])
            status = self.rng.choice(['양호', '부진', '안정적', '불안정'])
            
            if '{}%' in template:
                title = template.format(pct, direction)
            elif template.count('{}') == 2:
                title = template.format(status, direction)
            else:
                title = template.format(status)
            
            impact = round(self.rng.uniform(60, 95), 2)
            
            items.append(dataschemas.HighImpactNewsItem(
                title=title,
                impact=impact,
                rank=i + 1
            ))
        
        return items
    
    def _generate_category_summary(self) -> List[dataschemas.CategoryImpactItem]:
        """카테고리별 영향도 생성"""
        categories = list(self.FEATURE_CATEGORIES.keys())
        
        # 각 카테고리별 영향도 (합이 1)
        impacts = self.rng.dirichlet(np.ones(len(categories)))
        
        items = []
        for category, impact in zip(categories, impacts):
            items.append(dataschemas.CategoryImpactItem(
                category=category,
                impact_sum=round(float(impact * 100), 2),
                ratio=round(float(impact), 4)
            ))
        
        # 영향도 순으로 정렬
        items.sort(key=lambda x: x.impact_sum, reverse=True)
        
        return items
    
    def generate_news_list(self, n: int = 20) -> List[dataschemas.NewsResponse]:
        """
        뉴스 목록 생성
        
        Args:
            n: 생성할 뉴스 개수
        
        Returns:
            NewsResponse 리스트
        """
        news_templates = [
            ("미 농무부, 올해 곡물 생산량 전망 발표", "미국 농무부(USDA)가 올해 주요 곡물의 생산량 전망을 발표했습니다. 옥수수 생산량은..."),
            ("중국의 곡물 수입 증가 전망", "중국이 미국산 곡물 수입을 늘릴 것으로 예상됩니다. 이는 자국 내 수요 증가와..."),
            ("가뭄 우려로 작황 부진 예상", "주요 곡물 산지에서 가뭄 우려가 커지고 있습니다. 기상청은..."),
            ("달러 강세에 농산물 가격 하락", "최근 달러 강세로 인해 농산물 선물 가격이 하락하고 있습니다..."),
            ("국제 곡물 재고 증가, 가격 안정 전망", "국제 곡물 재고가 전년 대비 증가하면서 가격이 안정될 것으로..."),
            ("날씨 개선으로 작황 호조", "최근 강수량 증가로 주요 산지의 작황이 개선되고 있습니다..."),
            ("바이오연료 수요 증가로 곡물 가격 상승", "바이오연료 생산 확대로 인한 곡물 수요 증가가 예상됩니다..."),
            ("수출 수요 강세, 재고 감소 전망", "주요 수입국들의 수요 증가로 미국 곡물 수출이 강세를..."),
            ("FRB 금리 정책이 농산물 시장에 미치는 영향", "연준의 통화정책 변화가 농산물 선물 시장에도 영향을..."),
            ("글로벌 공급망 이슈로 물류 비용 상승", "국제 운송비 상승이 곡물 가격에 부담으로 작용하고 있습니다..."),
        ]
        
        news_list = []
        now = datetime.now()
        
        for i in range(n):
            # 랜덤 템플릿 선택
            title, content_start = self.rng.choice(news_templates)
            
            # 최근 7일 내 랜덤 날짜
            days_ago = int(self.rng.integers(0, 7))
            created_at = now - timedelta(days=days_ago)
            
            # 내용 확장
            content = content_start + " " + "분석가들은 이러한 요인들이 단기 가격에 영향을 미칠 것으로 전망하고 있습니다. " * 3
            
            news_list.append(dataschemas.NewsResponse(
                id=100000 + i,
                title=f"[{i+1}] {title}",
                content=content,
                source_url=f"https://news.example.com/article/{i+1}",
                created_at=created_at
            ))
        
        # 최신순 정렬
        news_list.sort(key=lambda x: x.created_at, reverse=True)
        
        return news_list
    
    def generate_simulation_result(
        self,
        base_date: date,
        original_predictions: List[dataschemas.TftPredResponse],
        feature_overrides: Dict[str, float],
        days: int = 60,
        current_values: Dict[str, float] = None
    ) -> List[dataschemas.SimulationPredictionItem]:
        """
        시뮬레이션 결과 생성 (빠른 더미 로직)
        
        Args:
            base_date: 기준 날짜
            original_predictions: 원본 예측 데이터
            feature_overrides: 변경할 feature들
            days: 예측 일수
            current_values: 현재 feature 값들 (Baseline으로 사용)
        
        Returns:
            SimulationPredictionItem 리스트
        """
        # Feature별 가격 영향 계수 (간단한 선형 모델)
        FEATURE_COEFFICIENTS = {
            '10Y_Yield': -0.05,  # 금리 10% 상승 → 가격 0.5% 하락 (민감도 조정)
            'USD_Index': -0.05,  # 달러 10% 상승 → 가격 0.5% 하락
            'pdsi': -0.02,       # 가뭄 지수 상승(습함) → 가격 하락
            'spi30d': -0.01,
            'spi90d': -0.01,
        }
        
        # Feature별 기본 기준값 (현재 값이 없을 경우 사용)
        DEFAULT_BASELINES = {
            '10Y_Yield': 4.0,    # 4.0%
            'USD_Index': 100.0,  # 100
            'pdsi': 0.0,         # 0 (중립)
            'spi30d': 0.0,
            'spi90d': 0.0,
        }
        
        if current_values is None:
            current_values = {}
        
        # 전체 가격 변화율 계산
        total_impact = 0.0
        for feature, new_value in feature_overrides.items():
            if feature in FEATURE_COEFFICIENTS:
                # 현재값 대비 변화율
                # DB에서 가져온 현재 값이 있으면 그것을 사용, 없으면 기본값
                baseline = current_values.get(feature, DEFAULT_BASELINES.get(feature, 100.0))
                
                # 0으로 나누기 방지
                if abs(baseline) < 1e-6:
                    # 기준값이 0인 경우(pdsi 등), 절대적 차이로 계산
                    change_ratio = new_value - baseline
                else:
                    change_ratio = (new_value - baseline) / baseline
                
                price_impact = change_ratio * FEATURE_COEFFICIENTS[feature]
                total_impact += price_impact
        
        # 결과 생성
        results = []
        
        # 원본 데이터가 없을 때를 대비한 패턴 파라미터
        phase_long = self.rng.uniform(0, 2 * np.pi)
        
        for i in range(days):
            pred_date = base_date + timedelta(days=i + 1)
            
            # 원본 가격 (있으면 사용, 없으면 생성)
            if i < len(original_predictions):
                original_price = float(original_predictions[i].price_pred)
            else:
                # 원본 데이터 부족 시 자연스러운 패턴 생성 (generate_predictions 로직과 유사)
                cycle_long = 0.02 * np.sin(2 * np.pi * i / 30 + phase_long)
                noise = self.rng.normal(0, 0.002)
                original_price = self.base_price * (1 + 0.001 * i + cycle_long + noise)
            
            # 시뮬레이션 가격: 원본 + 영향도
            # 일수가 지날수록 영향이 누적되도록 선형 증가
            cumulative_impact = total_impact * (i + 1) / days
            simulated_price = original_price * (1 + cumulative_impact)
            
            # 추가 노이즈 제거 (원본 패턴 유지)
            # simulated_price += self.rng.normal(0, original_price * 0.002)
            
            change = simulated_price - original_price
            change_percent = (change / original_price) * 100 if original_price != 0 else 0
            
            results.append(dataschemas.SimulationPredictionItem(
                date=pred_date.isoformat(),
                original_price=round(original_price, 2),
                simulated_price=round(simulated_price, 2),
                change=round(change, 2),
                change_percent=round(change_percent, 2)
            ))
        
        return results


# 전역 인스턴스 (재사용)
_generator = None

def get_generator(base_price: float = 450.0) -> DummyDataGenerator:
    """
    더미 데이터 생성기 싱글톤 가져오기
    
    Args:
        base_price: 기준 가격
    
    Returns:
        DummyDataGenerator 인스턴스
    """
    global _generator
    if _generator is None:
        _generator = DummyDataGenerator(base_price)
    return _generator

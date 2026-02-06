"""
모든 API 엔드포인트 통합 테스트

로컬 또는 EC2 서버의 모든 API가 정상 작동하는지 확인합니다.

실행 방법:
    # 로컬 테스트
    python tests/test_all_apis.py

    # EC2 테스트
    python tests/test_all_apis.py --base-url http://44.252.76.158:8000
"""

import requests
import argparse
from datetime import date, timedelta
import json
from typing import Dict, List


class APITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.passed = 0
        self.failed = 0
        self.test_results = []
        
    def print_header(self, title: str):
        """테스트 섹션 헤더 출력"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)
    
    def print_result(self, test_name: str, success: bool, message: str = ""):
        """테스트 결과 출력"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {test_name}")
        if message:
            print(f"       └─ {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
        
        if success:
            self.passed += 1
        else:
            self.failed += 1
    
    def test_root(self):
        """루트 엔드포인트 테스트"""
        self.print_header("1️⃣  서버 상태 확인")
        
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.print_result("GET /", True, f"응답: {data.get('message', 'OK')}")
            else:
                self.print_result("GET /", False, f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("GET /", False, f"Error: {str(e)}")
    
    def test_predictions_api(self):
        """예측 API 테스트"""
        self.print_header("2️⃣  예측 API (Predictions)")
        
        # 2-1. 최신 예측 목록 조회
        try:
            response = requests.get(
                f"{self.base_url}/api/predictions",
                params={"commodity": "corn"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                pred_count = len(data.get("predictions", []))
                price_count = len(data.get("historical_prices", []))
                self.print_result(
                    "GET /api/predictions?commodity=corn",
                    True,
                    f"예측 {pred_count}건, 과거가격 {price_count}건"
                )
            else:
                self.print_result(
                    "GET /api/predictions?commodity=corn",
                    False,
                    f"Status: {response.status_code}"
                )
        except Exception as e:
            self.print_result(
                "GET /api/predictions?commodity=corn",
                False,
                f"Error: {str(e)}"
            )
        
        # 2-2. 특정 날짜 예측 조회
        try:
            today = date.today()
            response = requests.get(
                f"{self.base_url}/api/predictions/{today.isoformat()}",
                params={"commodity": "corn"},
                timeout=10
            )
            if response.status_code in [200, 404]:
                if response.status_code == 200:
                    data = response.json()
                    self.print_result(
                        f"GET /api/predictions/{today.isoformat()}",
                        True,
                        f"날짜: {data.get('target_date', 'N/A')}"
                    )
                else:
                    self.print_result(
                        f"GET /api/predictions/{today.isoformat()}",
                        True,
                        "데이터 없음 (정상)"
                    )
            else:
                self.print_result(
                    f"GET /api/predictions/{today.isoformat()}",
                    False,
                    f"Status: {response.status_code}"
                )
        except Exception as e:
            self.print_result(
                f"GET /api/predictions/{today.isoformat()}",
                False,
                f"Error: {str(e)}"
            )
    
    def test_newsdb_api(self):
        """뉴스 API 테스트"""
        self.print_header("3️⃣  뉴스 API (NewsDB)")
        
        try:
            response = requests.get(
                f"{self.base_url}/api/newsdb",
                params={"limit": 5},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                count = len(data)
                if count > 0:
                    first_news = data[0]
                    self.print_result(
                        "GET /api/newsdb?limit=5",
                        True,
                        f"{count}건 조회, 최신: {first_news.get('title', '')[:30]}..."
                    )
                else:
                    self.print_result(
                        "GET /api/newsdb?limit=5",
                        True,
                        "뉴스 없음"
                    )
            else:
                self.print_result(
                    "GET /api/newsdb?limit=5",
                    False,
                    f"Status: {response.status_code}"
                )
        except Exception as e:
            self.print_result(
                "GET /api/newsdb?limit=5",
                False,
                f"Error: {str(e)}"
            )
    
    def test_market_metrics_api(self):
        """시장 지표 API 테스트"""
        self.print_header("4️⃣  시장 지표 API (Market Metrics)")
        
        try:
            today = date.today()
            response = requests.get(
                f"{self.base_url}/api/market-metrics",
                params={
                    "commodity": "corn",
                    "date": today.isoformat()
                },
                timeout=10
            )
            if response.status_code in [200, 404]:
                if response.status_code == 200:
                    data = response.json()
                    count = len(data.get("metrics", []))
                    self.print_result(
                        "GET /api/market-metrics",
                        True,
                        f"{count}개 지표"
                    )
                else:
                    self.print_result(
                        "GET /api/market-metrics",
                        True,
                        "데이터 없음 (정상)"
                    )
            else:
                self.print_result(
                    "GET /api/market-metrics",
                    False,
                    f"Status: {response.status_code}"
                )
        except Exception as e:
            self.print_result(
                "GET /api/market-metrics",
                False,
                f"Error: {str(e)}"
            )
    
    def test_simulation_api(self):
        """시뮬레이션 API 테스트"""
        self.print_header("5️⃣  시뮬레이션 API (Simulation)")
        
        try:
            today = date.today()
            payload = {
                "commodity": "corn",
                "base_date": today.isoformat(),
                "feature_overrides": {
                    "10Y_Yield": 4.5,
                    "USD_Index": 105.0,
                    "pdsi": -1.0
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/simulate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                change = data.get("change", 0)
                change_pct = data.get("change_percent", 0)
                self.print_result(
                    "POST /api/simulate",
                    True,
                    f"변화: ${change:.2f} ({change_pct:.2f}%)"
                )
            elif response.status_code == 400:
                error = response.json()
                self.print_result(
                    "POST /api/simulate",
                    False,
                    f"요청 오류: {error.get('detail', 'Unknown')}"
                )
            else:
                self.print_result(
                    "POST /api/simulate",
                    False,
                    f"Status: {response.status_code}"
                )
        except Exception as e:
            self.print_result(
                "POST /api/simulate",
                False,
                f"Error: {str(e)}"
            )
    
    def test_docs(self):
        """API 문서 접근 테스트"""
        self.print_header("6️⃣  API 문서")
        
        # Swagger UI
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=5)
            self.print_result(
                "GET /docs (Swagger UI)",
                response.status_code == 200,
                f"Status: {response.status_code}"
            )
        except Exception as e:
            self.print_result(
                "GET /docs (Swagger UI)",
                False,
                f"Error: {str(e)}"
            )
        
        # ReDoc
        try:
            response = requests.get(f"{self.base_url}/redoc", timeout=5)
            self.print_result(
                "GET /redoc",
                response.status_code == 200,
                f"Status: {response.status_code}"
            )
        except Exception as e:
            self.print_result(
                "GET /redoc",
                False,
                f"Error: {str(e)}"
            )
    
    def print_summary(self):
        """최종 결과 요약"""
        print("\n" + "=" * 80)
        print("  📊 테스트 결과 요약")
        print("=" * 80)
        
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n총 테스트: {total}개")
        print(f"✅ 통과: {self.passed}개")
        print(f"❌ 실패: {self.failed}개")
        print(f"통과율: {pass_rate:.1f}%")
        
        if self.failed > 0:
            print("\n⚠️  실패한 테스트:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n" + "=" * 80)
        
        if self.failed == 0:
            print("✅ 모든 테스트 통과!")
        else:
            print(f"⚠️  {self.failed}개 테스트 실패")
        print("=" * 80 + "\n")
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "🧪" * 40)
        print(f"  API 통합 테스트 시작")
        print(f"  서버: {self.base_url}")
        print("🧪" * 40)
        
        self.test_root()
        self.test_predictions_api()
        self.test_newsdb_api()
        self.test_market_metrics_api()
        self.test_simulation_api()
        self.test_docs()
        
        self.print_summary()
        
        return self.failed == 0


def main():
    parser = argparse.ArgumentParser(description="API 통합 테스트")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API 서버 URL (기본값: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    tester = APITester(base_url=args.base_url)
    success = tester.run_all_tests()
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()

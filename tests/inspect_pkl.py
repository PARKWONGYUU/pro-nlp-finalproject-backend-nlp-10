"""
PKL 파일 내용 확인
"""

import pickle
from pathlib import Path
import sys

def inspect_pkl(filepath):
    """PKL 파일 내용 검사"""
    print(f"\n{'='*60}")
    print(f"PKL 파일 분석: {filepath}")
    print(f"{'='*60}")
    
    path = Path(filepath)
    
    if not path.exists():
        print(f"❌ 파일이 존재하지 않습니다")
        return
    
    # 파일 크기
    size = path.stat().st_size
    print(f"📊 파일 크기: {size:,} bytes ({size / 1024:.2f} KB)")
    
    if size == 0:
        print(f"❌ 파일이 비어있습니다!")
        return
    
    try:
        # PKL 파일 로드
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        print(f"✅ PKL 파일 로드 성공!\n")
        
        # 데이터 타입
        print(f"📦 데이터 타입: {type(data)}")
        
        # Dictionary인 경우
        if isinstance(data, dict):
            print(f"\n📋 Dictionary 키 목록:")
            for key in data.keys():
                print(f"   - {key}")
            
            print(f"\n📊 각 키의 상세 정보:")
            for key, value in data.items():
                print(f"\n   🔑 '{key}':")
                print(f"      타입: {type(value)}")
                
                # Scaler 객체인 경우
                if hasattr(value, '__class__') and 'Scaler' in value.__class__.__name__:
                    print(f"      클래스: {value.__class__.__name__}")
                    if hasattr(value, 'mean_'):
                        print(f"      평균 (mean_): {value.mean_}")
                    if hasattr(value, 'scale_'):
                        print(f"      스케일 (scale_): {value.scale_}")
                    if hasattr(value, 'var_'):
                        print(f"      분산 (var_): {value.var_}")
                    if hasattr(value, 'n_features_in_'):
                        print(f"      Feature 개수: {value.n_features_in_}")
                    if hasattr(value, 'feature_names_in_'):
                        print(f"      Feature 이름: {value.feature_names_in_}")
                
                # 리스트인 경우
                elif isinstance(value, list):
                    print(f"      길이: {len(value)}")
                    print(f"      내용: {value}")
                
                # 기타
                else:
                    print(f"      값: {value}")
        
        # 리스트인 경우
        elif isinstance(data, list):
            print(f"\n📋 리스트 길이: {len(data)}")
            print(f"   내용: {data}")
        
        # 기타
        else:
            print(f"\n📋 내용: {data}")
        
        print(f"\n{'='*60}")
        print("✅ 분석 완료")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ PKL 파일 로드 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        # 기본값
        filepath = "temp/7d_preprocessing_20260206.pkl"
    
    inspect_pkl(filepath)

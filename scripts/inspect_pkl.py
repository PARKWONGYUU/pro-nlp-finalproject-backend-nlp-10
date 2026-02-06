"""PKL 파일 내용 확인"""
import pickle
import sys
from pathlib import Path

filepath = sys.argv[1] if len(sys.argv) > 1 else "temp/60d_preprocessing_20260206.pkl"

print(f"\n{'='*60}")
print(f"PKL 파일 분석: {filepath}")
print(f"{'='*60}\n")

with open(filepath, 'rb') as f:
    data = pickle.load(f)

print(f"타입: {type(data)}\n")

if isinstance(data, dict):
    print("Dictionary 키:")
    for key in data.keys():
        print(f"  - {key}")
    
    print("\n상세 정보:")
    for key, value in data.items():
        print(f"\n[{key}]")
        print(f"  타입: {type(value)}")
        
        if isinstance(value, list):
            print(f"  길이: {len(value)}")
            if len(value) < 20:
                print(f"  내용: {value}")
            else:
                print(f"  첫 10개: {value[:10]}")
        elif hasattr(value, 'shape'):
            print(f"  Shape: {value.shape}")
        else:
            val_str = str(value)
            if len(val_str) < 200:
                print(f"  값: {value}")
            else:
                print(f"  값: {val_str[:200]}...")

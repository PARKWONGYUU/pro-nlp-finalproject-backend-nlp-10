"""
ONNX 모델의 입력/출력 구조 상세 확인
"""

import onnxruntime as ort
from pathlib import Path

def inspect_onnx_model(filepath):
    """ONNX 모델의 입력/출력 상세 정보 확인"""
    print(f"\n{'='*70}")
    print(f"ONNX 모델 분석: {Path(filepath).name}")
    print(f"{'='*70}\n")
    
    try:
        # 세션 생성
        session = ort.InferenceSession(str(filepath), providers=['CPUExecutionProvider'])
        
        print("✅ 모델 로드 성공!\n")
        
        # 입력 정보
        inputs = session.get_inputs()
        print(f"📥 입력 (총 {len(inputs)}개):")
        print("-" * 70)
        
        for idx, inp in enumerate(inputs):
            print(f"\n[{idx}] 이름: {inp.name}")
            print(f"    Shape: {inp.shape}")
            print(f"    Type: {inp.type}")
            
            # 예제 데이터 형태 제시
            if 'lengths' in inp.name:
                print(f"    💡 예상: 시퀀스 길이 (정수)")
            elif 'cat' in inp.name:
                print(f"    💡 예상: 범주형 데이터")
            elif 'cont' in inp.name:
                print(f"    💡 예상: 연속형 데이터")
            elif 'scale' in inp.name:
                print(f"    💡 예상: 스케일링 파라미터")
        
        # 출력 정보
        outputs = session.get_outputs()
        print(f"\n\n📤 출력 (총 {len(outputs)}개):")
        print("-" * 70)
        
        for idx, out in enumerate(outputs):
            print(f"\n[{idx}] 이름: {out.name}")
            print(f"    Shape: {out.shape}")
            print(f"    Type: {out.type}")
        
        print("\n" + "="*70)
        print("💡 필요한 입력 데이터 구조")
        print("="*70)
        
        input_dict = {}
        for inp in inputs:
            input_dict[inp.name] = f"shape {inp.shape}"
        
        print("\n입력 dictionary 형태:")
        print("{")
        for name, shape in input_dict.items():
            print(f"    '{name}': {shape},")
        print("}")
        
        return True
        
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # temp 폴더의 ONNX 파일들 확인
    temp_path = Path("temp")
    onnx_files = list(temp_path.glob("*.onnx"))
    
    if not onnx_files:
        print("❌ temp 폴더에 ONNX 파일이 없습니다")
    else:
        for onnx_file in onnx_files:
            # 크기가 0이 아닌 파일만
            if onnx_file.stat().st_size > 100:
                inspect_onnx_model(str(onnx_file))

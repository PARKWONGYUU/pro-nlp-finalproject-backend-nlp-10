"""
ONNX 모델 파일 검증 스크립트
"""

import onnx
from pathlib import Path
import sys

def check_onnx_file(filepath):
    """ONNX 파일 검증"""
    print(f"\n{'='*60}")
    print(f"ONNX 파일 검증: {filepath}")
    print(f"{'='*60}")
    
    # 파일 존재 확인
    if not Path(filepath).exists():
        print(f"❌ 파일이 존재하지 않습니다: {filepath}")
        return False
    
    # 파일 크기 확인
    file_size = Path(filepath).stat().st_size
    print(f"📊 파일 크기: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
    
    if file_size == 0:
        print(f"❌ 파일이 비어있습니다!")
        return False
    
    try:
        # ONNX 모델 로드
        print(f"\n🔍 ONNX 모델 로딩 중...")
        model = onnx.load(filepath)
        
        # 모델 검증
        print(f"✅ ONNX 모델 로드 성공")
        
        print(f"\n📋 모델 정보:")
        print(f"   IR 버전: {model.ir_version}")
        print(f"   Producer: {model.producer_name} {model.producer_version}")
        print(f"   Domain: {model.domain}")
        print(f"   Model 버전: {model.model_version}")
        print(f"   Doc string: {model.doc_string[:100] if model.doc_string else 'N/A'}")
        
        # Graph 정보
        graph = model.graph
        print(f"\n📊 Graph 정보:")
        print(f"   이름: {graph.name}")
        print(f"   노드 수: {len(graph.node)}")
        print(f"   입력 수: {len(graph.input)}")
        print(f"   출력 수: {len(graph.output)}")
        
        # 입력 정보
        print(f"\n📥 입력 정보:")
        for idx, input_tensor in enumerate(graph.input):
            print(f"   [{idx}] 이름: {input_tensor.name}")
            # Shape 정보
            shape = []
            if input_tensor.type.tensor_type.shape:
                for dim in input_tensor.type.tensor_type.shape.dim:
                    if dim.dim_value:
                        shape.append(dim.dim_value)
                    elif dim.dim_param:
                        shape.append(dim.dim_param)
            print(f"       Shape: {shape}")
            print(f"       Type: {input_tensor.type.tensor_type.elem_type}")
        
        # 출력 정보
        print(f"\n📤 출력 정보:")
        for idx, output_tensor in enumerate(graph.output):
            print(f"   [{idx}] 이름: {output_tensor.name}")
            # Shape 정보
            shape = []
            if output_tensor.type.tensor_type.shape:
                for dim in output_tensor.type.tensor_type.shape.dim:
                    if dim.dim_value:
                        shape.append(dim.dim_value)
                    elif dim.dim_param:
                        shape.append(dim.dim_param)
            print(f"       Shape: {shape}")
            print(f"       Type: {output_tensor.type.tensor_type.elem_type}")
        
        # 모델 검증
        print(f"\n🔍 모델 검증 중...")
        onnx.checker.check_model(model)
        print(f"✅ 모델 검증 성공!")
        
        return True
        
    except onnx.onnx_cpp2py_export.checker.ValidationError as e:
        print(f"❌ ONNX 모델 검증 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 함수"""
    print("\n" + "🔍"*30)
    print("ONNX 모델 검증 도구")
    print("🔍"*30)
    
    # temp 폴더의 모든 ONNX 파일 검색
    temp_path = Path("./temp")
    
    if not temp_path.exists():
        print(f"❌ temp 폴더가 존재하지 않습니다")
        sys.exit(1)
    
    onnx_files = list(temp_path.glob("*.onnx"))
    
    if not onnx_files:
        print(f"❌ temp 폴더에 ONNX 파일이 없습니다")
        sys.exit(1)
    
    print(f"\n📁 발견된 ONNX 파일: {len(onnx_files)}개")
    for f in onnx_files:
        print(f"   - {f.name}")
    
    # 각 파일 검증
    results = []
    for onnx_file in onnx_files:
        success = check_onnx_file(str(onnx_file))
        results.append((onnx_file.name, success))
    
    # 최종 결과
    print(f"\n{'='*60}")
    print("🎯 검증 결과 요약")
    print(f"{'='*60}")
    
    for filename, success in results:
        status = "✅ 정상" if success else "❌ 오류"
        print(f"{status} {filename}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n✅ 모든 ONNX 파일이 정상입니다!")
    else:
        print("\n❌ 일부 ONNX 파일에 문제가 있습니다.")
        print("\n💡 해결 방법:")
        print("   1. ONNX 파일을 다시 생성하세요")
        print("   2. PyTorch 모델을 ONNX로 올바르게 변환했는지 확인하세요")
        print("   3. 파일이 완전히 다운로드/복사되었는지 확인하세요")
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()

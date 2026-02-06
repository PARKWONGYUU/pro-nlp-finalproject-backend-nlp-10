"""
temp/ 폴더의 파일 정보 확인
"""

from pathlib import Path
import struct

def check_file_info(filepath):
    """파일 기본 정보 확인"""
    print(f"\n{'='*60}")
    print(f"파일: {filepath.name}")
    print(f"{'='*60}")
    
    if not filepath.exists():
        print(f"❌ 파일이 존재하지 않습니다")
        return False
    
    # 파일 크기
    size = filepath.stat().st_size
    print(f"📊 파일 크기: {size:,} bytes ({size / 1024:.2f} KB)")
    
    if size == 0:
        print(f"❌ 파일이 비어있습니다!")
        return False
    
    # ONNX 파일인 경우 헤더 확인
    if filepath.suffix == '.onnx':
        try:
            with open(filepath, 'rb') as f:
                # ONNX는 Protobuf 형식
                header = f.read(100)
                
                print(f"\n📋 파일 헤더 (첫 100 bytes):")
                print(f"   Hex: {header[:20].hex()}")
                
                # ONNX 파일은 일반적으로 protobuf로 시작
                # Protobuf 메시지는 특정 바이트 패턴으로 시작
                if header[:4] == b'\x08\x03' or b'ir_version' in header or b'graph' in header:
                    print(f"   ✅ ONNX/Protobuf 형식으로 보입니다")
                else:
                    print(f"   ⚠️ ONNX 파일 형식이 아닐 수 있습니다")
                    print(f"   첫 20 bytes: {header[:20]}")
                
        except Exception as e:
            print(f"❌ 파일 읽기 오류: {e}")
            return False
    
    # PKL 파일인 경우
    elif filepath.suffix == '.pkl':
        try:
            with open(filepath, 'rb') as f:
                header = f.read(10)
                
                print(f"\n📋 파일 헤더:")
                print(f"   Hex: {header.hex()}")
                
                # Pickle 파일은 특정 magic number로 시작
                if header[0:1] == b'\x80':  # Pickle protocol 2+
                    protocol = header[1]
                    print(f"   ✅ Pickle 파일 (Protocol {protocol})")
                else:
                    print(f"   ⚠️ Pickle 형식이 아닐 수 있습니다")
                
        except Exception as e:
            print(f"❌ 파일 읽기 오류: {e}")
            return False
    
    return True

def main():
    """메인 함수"""
    print("\n" + "📁"*30)
    print("temp/ 폴더 파일 검사")
    print("📁"*30)
    
    temp_path = Path("temp")
    
    if not temp_path.exists():
        print(f"❌ temp 폴더가 존재하지 않습니다")
        return
    
    # 모든 파일 찾기
    all_files = list(temp_path.glob("*"))
    
    if not all_files:
        print(f"❌ temp 폴더가 비어있습니다")
        return
    
    print(f"\n📋 발견된 파일: {len(all_files)}개")
    
    onnx_files = []
    pkl_files = []
    other_files = []
    
    for f in all_files:
        if f.suffix == '.onnx':
            onnx_files.append(f)
        elif f.suffix == '.pkl':
            pkl_files.append(f)
        else:
            other_files.append(f)
    
    print(f"   - ONNX 파일: {len(onnx_files)}개")
    print(f"   - PKL 파일: {len(pkl_files)}개")
    print(f"   - 기타 파일: {len(other_files)}개")
    
    # 각 파일 검사
    for f in onnx_files + pkl_files + other_files:
        check_file_info(f)
    
    # ONNX Runtime으로 로드 테스트
    if onnx_files:
        print(f"\n{'='*60}")
        print("🔍 ONNX Runtime 로드 테스트")
        print(f"{'='*60}")
        
        try:
            import onnxruntime as ort
            
            for onnx_file in onnx_files:
                print(f"\n테스트: {onnx_file.name}")
                try:
                    session = ort.InferenceSession(
                        str(onnx_file),
                        providers=['CPUExecutionProvider']
                    )
                    
                    print(f"   ✅ 로드 성공!")
                    
                    # 입력/출력 정보
                    inputs = session.get_inputs()
                    outputs = session.get_outputs()
                    
                    print(f"   입력: {len(inputs)}개")
                    for inp in inputs:
                        print(f"      - {inp.name}: {inp.shape} ({inp.type})")
                    
                    print(f"   출력: {len(outputs)}개")
                    for out in outputs:
                        print(f"      - {out.name}: {out.shape} ({out.type})")
                    
                except Exception as e:
                    print(f"   ❌ 로드 실패: {e}")
        
        except ImportError:
            print(f"   ⚠️ onnxruntime이 설치되지 않아 테스트를 건너뜁니다")

if __name__ == "__main__":
    main()

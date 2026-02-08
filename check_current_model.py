"""
현재 사용 중인 모델 정보 확인
"""
import os
from app.config import settings
from app.ml.model_loader import get_model_loader

print('=' * 80)
print('현재 사용 중인 모델 정보')
print('=' * 80)
print()

# 설정 정보
print('📋 설정:')
print(f'  모드: {settings.model_load_mode}')
print(f'  로컬 경로: {settings.local_model_path}')

if settings.model_load_mode == 's3':
    print(f'  S3 버킷: {settings.model_s3_bucket}')
    print(f'  S3 프리픽스: {settings.model_s3_prefix}')
    print(f'  AWS 리전: {settings.aws_region}')
    print(f'  AWS Key ID: {settings.aws_access_key_id[:10]}...' if settings.aws_access_key_id else '  AWS Key ID: None')

print()
print('=' * 80)

# 모델 로더 정보
print('🤖 로드된 모델:')
print()

try:
    loader = get_model_loader()
    
    # 로드 시도
    commodity = 'corn'
    print(f'Commodity: {commodity}')
    print()
    
    # 세션 로드 (캐싱됨)
    session = loader.load_session(commodity)
    
    # 로드된 키 정보
    if commodity in loader._loaded_keys:
        keys = loader._loaded_keys[commodity]
        print('  📦 로드된 파일:')
        print(f'    ONNX: {keys.get("onnx_key", "N/A")}')
        print(f'    PKL:  {keys.get("pkl_key", "N/A")}')
        print()
    
    # ETag 정보
    if commodity in loader._etags:
        etags = loader._etags[commodity]
        print('  🔖 ETag (캐시):')
        print(f'    Model: {etags.get("model", "N/A")}')
        print(f'    PKL:   {etags.get("pkl", "N/A")}')
        print()
    
    # 세션 정보
    print('  🧠 ONNX 세션 정보:')
    print(f'    Providers: {session.get_providers()}')
    
    # 입력/출력 정보
    inputs = session.get_inputs()
    outputs = session.get_outputs()
    
    print(f'    입력 개수: {len(inputs)}')
    for i, inp in enumerate(inputs[:3]):  # 처음 3개만
        print(f'      [{i}] {inp.name}: {inp.shape} ({inp.type})')
    if len(inputs) > 3:
        print(f'      ... 외 {len(inputs) - 3}개')
    
    print(f'    출력 개수: {len(outputs)}')
    for i, out in enumerate(outputs[:3]):  # 처음 3개만
        print(f'      [{i}] {out.name}: {out.shape} ({out.type})')
    if len(outputs) > 3:
        print(f'      ... 외 {len(outputs) - 3}개')
    
    print()
    
    # 전처리 정보
    preprocessing = loader.get_preprocessing_info(commodity)
    if preprocessing:
        print('  📊 전처리 정보:')
        for key, value in list(preprocessing.items())[:5]:  # 처음 5개만
            print(f'    {key}: {type(value).__name__}')
        if len(preprocessing) > 5:
            print(f'    ... 외 {len(preprocessing) - 5}개')
    else:
        print('  ⚠️  전처리 정보 없음')
    
    print()
    print('=' * 80)
    print('✅ 모델 로드 성공!')
    print('=' * 80)
    
    # S3 모드인 경우 최신 파일 확인
    if settings.model_load_mode == 's3':
        print()
        print('🔍 S3에서 최신 파일 확인 중...')
        
        import boto3
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        
        prefix = settings.model_s3_prefix.rstrip("/") + "/"
        
        response = s3.list_objects_v2(
            Bucket=settings.model_s3_bucket,
            Prefix=prefix,
            MaxKeys=10
        )
        
        if 'Contents' in response:
            print(f'\nS3에 있는 파일 (s3://{settings.model_s3_bucket}/{prefix}):')
            for obj in sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True):
                key = obj['Key']
                filename = key.rsplit("/", 1)[-1]
                size_mb = obj['Size'] / (1024 * 1024)
                modified = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                print(f'  📄 {filename}')
                print(f'     크기: {size_mb:.2f} MB')
                print(f'     수정: {modified}')
                print()
        else:
            print('  ⚠️  S3에 파일이 없습니다.')
    
except Exception as e:
    print(f'❌ 오류: {e}')
    import traceback
    traceback.print_exc()

print()
print('=' * 80)
print('💡 S3 파일명 패턴:')
print('  - ONNX: 60d_YYYYMMDD.onnx')
print('  - PKL:  60d_preprocessing_YYYYMMDD.pkl')
print('  - 예: 60d_20260206.onnx')
print('=' * 80)

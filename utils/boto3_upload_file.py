import os
import uuid
import boto3
from runpod import RunPodLogger
from dotenv import load_dotenv

log = RunPodLogger()

load_dotenv()

def s3_file_upload(file_path: str, minutes: int = 60) -> str:
    """
    期限付き公開URLのみ返す
    
    Args:
        file_path: ローカルのファイルパス
        minutes: URLの公開期限
    
    Returns:
        期限付きurl        
    """
    s3 = boto3.client('s3')
    bucket = os.getenv('BUCKET_NAME')
    
    # ファイル拡張子を保持しながらUUID名に変更
    file_extension = os.path.splitext(file_path)[1]  # .pngなど
    key = f"{uuid.uuid4()}{file_extension}"
    
    try:
        
        s3.upload_file(file_path, bucket, key)

        # 期限付きURL生成
        return s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=minutes * 60
        )
    
    except Exception as e:
        log.error(f"ファイルアップロードに失敗しました: {e}")
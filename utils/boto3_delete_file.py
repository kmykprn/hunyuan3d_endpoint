import os
import boto3
from dotenv import load_dotenv
from runpod import RunPodLogger
from urllib.parse import urlparse

log = RunPodLogger()

load_dotenv()

def s3_delete_from_url(s3_url: str) -> bool:
    """
    S3 URLからファイル削除
    
    Args:
        s3_url: 対象ファイルのurl
    
    Returns:
        成功判定のBool値（Trueで成功、Falseで失敗）
    """
    try:
        s3 = boto3.client('s3')
        bucket = os.getenv('BUCKET_NAME')
        
        # URLからキーを抽出（presigned URLの場合、パスの先頭の'/'を除去）
        parsed_url = urlparse(s3_url)
        key = parsed_url.path.lstrip('/')  # ファイル名部分を取得
        
        s3.delete_object(Bucket=bucket, Key=key)
        return True
    
    except Exception as e:
        log.error(f"ファイル削除に失敗しました: {e}")
        return False
import os

import boto3

# ローカル実行時は.envファイルから環境変数を読み込む
if os.path.exists(".env"):
    from dotenv import load_dotenv

    load_dotenv()


# グローバルクライアント（一度だけ初期化）
def get_s3_client():
    """S3クライアントを取得（シングルトンパターン）"""
    if not hasattr(get_s3_client, "_client"):
        # エンドポイントURLが設定されている場合は使用（MinIOなどの互換サービス対応）
        endpoint_url = os.getenv("BUCKET_ENDPOINT_URL")

        client_params = {
            "service_name": "s3",
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "region_name": os.getenv("AWS_DEFAULT_REGION"),
        }

        # AWS S3の標準URLの場合は指定しない（自動選択される）
        if endpoint_url and "s3.amazonaws.com" not in endpoint_url:
            client_params["endpoint_url"] = endpoint_url

        get_s3_client._client = boto3.client(**client_params)
    return get_s3_client._client


def get_bucket_name():
    """バケット名を取得"""
    return os.getenv("BUCKET_NAME")

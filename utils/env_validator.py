import os
from typing import List, Optional

from runpod import RunPodLogger

log = RunPodLogger()

if os.path.exists(".env"):
    from dotenv import load_dotenv

    load_dotenv()


def validate_environment(required_vars: Optional[List[str]] = None) -> None:
    """
    必須環境変数を検証

    Args:
        required_vars: 検証する環境変数のリスト。
                      Noneの場合はデフォルトの必須環境変数を使用

    Raises:
        ValueError: 必須環境変数が設定されていない場合
    """
    if required_vars is None:
        # デフォルトの必須環境変数
        required_vars = [
            "SYNEXA_API_KEY",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_DEFAULT_REGION",
            "BUCKET_NAME",
            # BUCKET_ENDPOINT_URLはオプション（S3互換サービス使用時のみ）
        ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            log.error(f"環境変数 {var} が設定されていません")

    if missing_vars:
        error_msg = f"必須環境変数が設定されていません: {', '.join(missing_vars)}"
        log.error(error_msg)
        raise ValueError(error_msg)

    log.info("環境変数の検証が完了しました")

from runpod import RunPodLogger

from utils.boto3_client import get_bucket_name, get_s3_client

log = RunPodLogger()


class S3Utils:
    def __init__(self) -> None:
        self.s3 = get_s3_client()
        self.bucket = get_bucket_name()

    def delete_file(self, key: str) -> bool:
        """
        S3上で指定したファイル名を削除

        Args:
            key: 削除するファイル名

        Returns:
            成功判定のBool値（Trueで成功、Falseで失敗）
        """
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=key)
            return True

        except Exception as e:
            log.error(f"ファイル削除に失敗しました: {e}")
            return False

    def upload_from_server(self, file_path: str, key: str, minutes: int = 60):
        """
        バックエンドサーバからS3にファイルをアップロードし、期限付き公開URLのみ返す

        Args:
            file_path: ローカルのファイルパス
            key: アップロード後の、s3上でのファイル名(uuid.pngを想定)
            minutes: URLの公開期限

        Returns:
            期限付きダウンロードリンク
        """
        try:
            self.s3.upload_file(file_path, self.bucket, key)

            # 期限付きURL生成
            return self.s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=minutes * 60,
            )

        except Exception as e:
            log.error(f"ファイルアップロードに失敗しました: {e}")

        return None

    def generate_upload_url_for_client(self, key: str, minutes: int = 60):
        """
        フロントエンド用：アップロード用の事前署名URLを生成

        Args:
            key: アップロード後の、s3上でのファイル名(uuid.pngを想定)
            minutes: URLの有効期限(分)

        Returns:
            "upload_url": "アップロード用URL"
        """
        try:
            # アップロード用事前署名URL
            upload_url = self.s3.generate_presigned_url(
                "put_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=minutes * 60,
            )
            return upload_url

        except Exception as e:
            log.error(f"URL生成に失敗しました: {e}")

        return None

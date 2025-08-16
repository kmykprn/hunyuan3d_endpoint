import os
from urllib.parse import urlparse

import requests

from utils.boto3_utils import S3Utils

test_local_file = "test/assets/sample.png"  # テスト用の画像ファイル
test_key = "test-file-name-4dbc-6a17c86ec41e.png"  # s3上でのファイル名

s3utils = S3Utils()


def extract_base_url(full_url: str) -> str:
    """URLからファイル名を抽出"""
    parsed = urlparse(full_url)
    return os.path.basename(parsed.path)


def upload_file_to_presigned_url(file_path: str, upload_url: str) -> bool:
    """事前署名URLにファイルをアップロード(フロント用機能が動作するかを確認する関数)"""
    try:
        with open(file_path, "rb") as f:
            response = requests.put(upload_url, data=f)
        return response.status_code == 200
    except Exception as e:
        print(e)
        return response.status_code == 500


def test_バックエンドサーバからS3にファイルアップロードができること():
    """
    確認観点：
        アップロードしたファイルのurlが取得され、ファイル名が指定したものであること
    """
    url = s3utils.upload_from_server(file_path=test_local_file, key=test_key)
    filename_on_s3 = extract_base_url(url)
    assert filename_on_s3 == test_key

    # ファイルの削除
    s3utils.delete_file(test_key)


def test_s3のファイルが削除できること():
    """
    確認観点：
        アップロードしたファイルが削除されていること
    """
    # 事前準備：ファイルのアップロード
    s3utils.upload_from_server(file_path=test_local_file, key=test_key)

    # ファイルの削除
    is_deleted = s3utils.delete_file(test_key)
    assert is_deleted == True  # noqa: E712


def test_クライアントからs3にファイルアップロードするurlが取得でき実際にアップロードできること():
    """
    確認観点：
        事前承認済みURLにファイルがアップロードできること
    """
    # URLを作成
    upload_url = s3utils.generate_upload_url_for_client(key=test_key)
    if upload_url:
        filename_on_s3 = extract_base_url(upload_url)
        assert filename_on_s3 == test_key

    # URLにアップロードできるか確認
    if upload_url:
        upload_success = upload_file_to_presigned_url(test_local_file, upload_url)
        assert upload_success == True  # noqa: E712

    # クリーンアップ
    s3utils.delete_file(test_key)

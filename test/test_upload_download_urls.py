import requests

from rp_handler import handler
from utils.boto3_utils import S3Utils

s3utils = S3Utils()


def test_アップロードアクションで両方のURLが生成されること():
    """
    確認観点：
        1. upload_urlとdownload_urlの両方が返される
        2. 両方のURLが同じkeyを参照している
        3. keyが正しい拡張子を持っている
    """
    # PNG拡張子でテスト
    event = {"input": {"action": "upload", "upload_file_extension": ".png"}}

    result = handler(event)

    # 必要なフィールドが含まれているか確認
    assert "upload_url" in result
    assert "download_url" in result
    assert "key" in result

    # keyが.pngで終わっているか確認
    assert result["key"].endswith(".png")

    # 両方のURLに同じkeyが含まれているか確認
    assert result["key"] in result["upload_url"]
    assert result["key"] in result["download_url"]

    print(f"✅ Generated key: {result['key']}")


def test_異なる拡張子でも正しくURLが生成されること():
    """
    確認観点：
        JPG、JPEG、GIFなど異なる拡張子でも動作する
    """
    extensions = [".jpg", "jpeg", ".gif", ".png"]  # 'jpeg'は.なし

    for ext in extensions:
        event = {"input": {"action": "upload", "upload_file_extension": ext}}

        result = handler(event)

        # 拡張子が正しく処理されているか
        expected_ext = ext if ext.startswith(".") else f".{ext}"
        assert result["key"].endswith(expected_ext)

        print(f"✅ Extension {ext} → key: {result['key']}")


def test_アップロードしたファイルが両方のURLで正しくアクセスできること():
    """
    確認観点：
        1. upload_urlでファイルをアップロード
        2. download_urlでファイルをダウンロード
        3. 両方が同じファイルを参照している
    """
    # URLを生成
    event = {"input": {"action": "upload", "upload_file_extension": ".png"}}

    result = handler(event)
    upload_url = result["upload_url"]
    download_url = result["download_url"]
    key = result["key"]

    # テストデータをアップロード
    test_data = b"test image data for URL verification"

    # upload_urlにPUT
    upload_response = requests.put(
        upload_url, data=test_data, headers={"Content-Type": "image/png"}
    )
    assert upload_response.status_code == 200
    print(f"✅ Uploaded to: {key}")

    # download_urlでGET
    download_response = requests.get(download_url)
    assert download_response.status_code == 200
    assert download_response.content == test_data
    print(f"✅ Downloaded from: {key}")

    # クリーンアップ
    s3utils.delete_file(key)
    print(f"🗑️  Cleaned up: {key}")


def test_download_urlがHunyuan3D_APIで使用可能な形式であること():
    """
    確認観点：
        生成されたdownload_urlが外部APIで使用可能な形式
    """
    event = {"input": {"action": "upload", "upload_file_extension": ".png"}}

    result = handler(event)
    download_url = result["download_url"]

    # URLが正しい形式か確認
    assert download_url.startswith("https://")
    assert "s3" in download_url or "amazonaws" in download_url
    assert "Expires=" in download_url  # 期限付きURL
    assert "Signature=" in download_url  # 署名付き

    # Content-Typeは含まれないべき（download用なので）
    assert "content-type" not in download_url.lower()

    print("Download URL format is correct")
    print(f"   URL: ...{download_url[-80:]}")


def test_URLの有効期限が正しく設定されていること():
    """
    確認観点：
        デフォルトで60分の有効期限が設定されている
    """
    import time
    from urllib.parse import parse_qs, urlparse

    event = {"input": {"action": "upload", "upload_file_extension": ".png"}}

    result = handler(event)

    # URLから有効期限を抽出
    parsed = urlparse(result["download_url"])
    params = parse_qs(parsed.query)

    if "Expires" in params:
        expires = int(params["Expires"][0])
        current_time = int(time.time())

        # 有効期限が現在時刻より後か
        assert expires > current_time

        # 約60分後（3600秒）か確認（誤差30秒許容）
        time_diff = expires - current_time
        assert 3570 <= time_diff <= 3630

        print(f"✅ URL expires in {time_diff} seconds (≈60 minutes)")

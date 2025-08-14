import os
from runpod import RunPodLogger
from urllib.parse import urlparse
from runpod.serverless.utils.rp_upload import upload_image


log = RunPodLogger()


def upload_textures_s3(job_id: str, textures_path: list[str]) -> list[str]:
    """
    AWS S3にテクスチャを保存し、テクスチャのURLを取得
    
    Args:
        job_id: ユニークID。今回はGLBファイルの保存ディレクトリ名（UUID4）を指定。
        textures_path: ローカルに保存されたテクスチャのパス(list)
    
    Returns:
        textures_url: s3にアップロードされたテクスチャのurl（list）
    """
    textures_url = []
    for texture_path in textures_path:
        
        # S3にテクスチャを保存
        texture_url = upload_image(job_id, texture_path)
        textures_url.append(texture_url)
    
    return textures_url


def remove_textures_file(url_list: list[str]):
    """
    /runpod-volumeから使い終わったファイルを削除する（サーバレス実行時専用）
    
    詳細：
        upload_image関数を使用して返ってくるurlは、/runpod-volumeと対応づいている。
        そのため、urlから特定の部分（ファイル名）を抽出し、/runpod-volume/と結合して、
        /runpod-volume/配下のファイル名を直接指定し、os.removeでファイルを削除する。
    
    Args:
        url_list: s3のurlリスト
    """
    for url in url_list:
        try:
            file_path = f"/runpod-volume/{urlparse(url).path.lstrip('/')}"

            # runpod上で動作しているとき
            if os.path.exists("/runpod-volume"):
                if os.path.exists(file_path):
                    os.remove(file_path)

            # ローカルで動作しているとき
            else:
                print(file_path)
                
        except Exception as e:
            log.error(f"Failed to delete {url}: {e}")

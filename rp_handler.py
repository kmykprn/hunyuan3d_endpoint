import os

import runpod
from runpod import RunPodLogger
from runpod.serverless.utils.rp_cleanup import clean

from utils.boto3_utils import S3Utils
from utils.env_validator import validate_environment
from utils.glb_utils import extract_texture_from_glb, fetch_glb_from_url
from utils.uuid import generate_uuid

log = RunPodLogger()

# ローカル開発環境でのみdotenvを使用
if os.path.exists(".env"):
    from dotenv import load_dotenv

    load_dotenv()

# 起動時に環境変数を検証
validate_environment()

# 環境変数取得（検証済みなので安全）
api_key = os.getenv("SYNEXA_API_KEY")

# S3Utilsのインスタンス化（環境変数検証済み）
s3utils = S3Utils()

import synexa  # noqa: E402

client = synexa.Synexa(api_key=api_key)


def fetch_3d_model(input_data) -> str:
    """
    外部APIから3Dモデルを取得する

    input_data:
        {
            "image_path": "***.png",
            "prompt": "",
            "timeout": 300
        }

    Returns:
        glb_url: glbファイルのURL
    """

    # 入力値を取得
    image_path = input_data.get("image_path")
    prompt = input_data.get("prompt", "")
    timeout = input_data.get("timeout", 300)

    # 入力検証
    if not image_path:
        raise ValueError("image_path is required")

    # 外部APIにリクエストを投げる
    output = client.run(
        "tencent/hunyuan3d-2",
        input={
            "seed": 1234,
            "image": image_path,
            "steps": 5,
            "caption": prompt,
            "shape_only": False,
            "guidance_scale": 5.5,
            "multiple_views": [],
            "check_box_rembg": True,
            "octree_resolution": "256",
        },
        wait=timeout,
    )

    # GLBファイルURLを返却
    glb_url = None
    for f in output:
        if "textured_mesh" in f.url:
            glb_url = f.url
            return glb_url

    # GLBファイルURLが見つからない場合は異常終了
    if not glb_url:
        log.error("テクスチャ付メッシュ生成のAPIに失敗しました")
        raise ValueError("No textured mesh found in API response")

    return ""


def handler(event):
    log.info("ジョブを受信しました。")

    input_data = event["input"]
    action = input_data["action"]

    # クライアント用の画像アップロードURLを取得
    if action == "upload":
        try:
            # クライアントから拡張子を受け取る（デフォルトは.png）
            file_extension = input_data.get("upload_file_extension", ".png")

            # 拡張子が.で始まっていない場合は追加
            if not file_extension.startswith("."):
                file_extension = f".{file_extension}"

            key = generate_uuid(file_extension=file_extension)
            upload_url = s3utils.generate_upload_url_for_client(key=key)
            return {"upload_url": upload_url, "key": key}

        except Exception as e:
            log.error(f"アップロード用URL生成に失敗しました: {e}")
            return {"error": "アップロード用URL生成に失敗しました"}

    # サーバ側でGLBファイルからテクスチャを抽出してS3にアップロードする
    elif action == "create":
        glb_dir = None

        try:
            # glbファイルのurlを取得
            glb_url = fetch_3d_model(input_data=input_data)

            # URLからglbファイルを取得し、ディレクトリに保存
            glb_dir, glb_filename = fetch_glb_from_url(glb_url)

            # glbファイルからテクスチャを取り出し、glbファイルと同じ場所にpng形式で保存
            textures_paths = extract_texture_from_glb(
                glb_dir=glb_dir, glb_filename=glb_filename
            )

            # テクスチャファイルをs3にアップロードし、ダウンロード用urlを取得
            textures_urls = []
            keys = []
            for path in textures_paths:
                key = generate_uuid(file_extension=".png")
                url = s3utils.upload_from_server(path, key)

                keys.append(key)
                textures_urls.append(url)

            # 成功時のレスポンス
            log.info("処理が正常に完了しました。")
            return {
                "glb_url": glb_url,  # SYNEXA上のGLBファイルのURL
                "textures_url": textures_urls,  # s3上のテクスチャのURL
                "keys": keys,  # s3上のテクスチャのファイル名
            }

        # エラー時のレスポンス（RunPod推奨形式）
        except Exception as e:
            log.error(f"GLB作成時にエラーが発生しました: {str(e)}")
            return {"error": f"GLB作成時にエラーが発生しました: {str(e)}"}

        # 一時ファイルのクリーンアップ
        finally:
            if glb_dir:
                try:
                    clean(folder_list=[glb_dir])
                except Exception as e:
                    # クリーンアップの失敗は無視
                    log.error(f"ファイル削除時にエラーが発生しました: {str(e)}")
                    pass

    # s3上の不要データを削除する
    elif action == "delete":
        try:
            all_file_deleted = True

            # S3上でファイル名を指定して削除
            for key in input_data["keys"]:
                is_deleted = s3utils.delete_file(key)
                if not is_deleted:
                    log.error(f"ファイル削除に失敗しました: {key}")
                    all_file_deleted = False

            if all_file_deleted:
                return {
                    "message": "すべてのファイルが削除されました",
                }
        except Exception as e:
            log.error(f"ファイル削除処理でエラーが発生しました：{e}")
            return {"error": f"ファイル削除処理でエラーが発生しました：{e}"}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})

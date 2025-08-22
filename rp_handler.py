import os

# flake8: noqa: E402
import runpod
from runpod import RunPodLogger
from runpod.serverless.utils.rp_cleanup import clean

# generatorsモジュールをインポート
from core.generators import external_generator, hunyuan_generator
from utils.boto3_utils import S3Utils
from utils.env_validator import validate_environment
from utils.glb_utils import fetch_glb_from_url
from utils.uuid import generate_uuid

log = RunPodLogger()

# ローカル開発環境でのみdotenvを使用
if os.path.exists(".env"):
    from dotenv import load_dotenv

    load_dotenv()

# 起動時に環境変数を検証
validate_environment()

# S3Utilsのインスタンス化（環境変数検証済み）
s3utils = S3Utils()


def create_glb_file(input_data: dict):
    """
    GLB形式の3Dモデルを作成し、s3にアップロードしてURLを返す

    Args:
        "input": {
            "image_path": "",
            "prompt": "",
            "timeout": 300,
            "action": "create",
            "model_name": "hunyuan3d",
            "use_texture": false
        }

    Returns:
        tmp_dir: ローカルのglbが格納されているディレクトリ名
        glb_filename: ローカルのglbファイル名
        glb_url: s3上のurl
    """
    tmp_dir = None
    glb_url = None

    # AIモデル名を取得（デフォルトはtriposr）
    model_name = input_data.get("model_name", "triposr")

    if model_name == "hunyuan3d":
        # ローカルでHunyuan3D-2を使用して3Dモデルを生成
        glb_path = hunyuan_generator.create_3d_model_hunyuan(input_data=input_data)

        # GLBファイルのディレクトリとファイル名を取得
        tmp_dir = os.path.dirname(glb_path)

    elif model_name == "hunyuan3d_ex":
        # 外部APIを使用して3Dモデルを取得
        glb_url = external_generator.fetch_3d_model(input_data=input_data)

        # URLからglbファイルを取得し、ディレクトリに保存
        tmp_dir, glb_filename = fetch_glb_from_url(glb_url)

        # glbファイルのローカルパスを取得
        glb_path = os.path.join(tmp_dir, glb_filename)
    else:
        raise ValueError(f"Unknown model_name: {model_name}")

    # GLBファイルをS3にアップロード
    glb_key = generate_uuid(file_extension=".glb")
    glb_url = s3utils.upload_from_server(glb_path, glb_key)
    log.info(f"GLBファイルをS3にアップロードしました: {glb_url}")

    return tmp_dir, glb_url, glb_key


def handler(event):
    log.info("ジョブを受信しました。")

    input_data = event["input"]
    action = input_data["action"]

    # クライアント用の画像アップロードURLを取得
    if action == "upload":
        try:
            # クライアントから拡張子を受け取る（デフォルトは.png）
            file_extension = input_data.get("upload_file_extension", ".png")

            # s3上でのファイル名を生成
            key = generate_uuid(file_extension=file_extension)

            # アップロード用urlを作成
            upload_url = s3utils.generate_upload_url_for_client(
                key=key, file_extension=file_extension
            )

            # ダウンロード用URLを生成
            download_url = s3utils.generate_download_url(key=key)

            return {"upload_url": upload_url, "download_url": download_url, "key": key}

        except Exception as e:
            log.error(f"アップロード用URL生成に失敗しました: {e}")
            return {"error": "アップロード用URL生成に失敗しました"}

    # サーバ側でGLBファイルを生成してS3にアップロードする
    elif action == "create":
        tmp_dir = None
        glb_url = None

        try:
            # glb形式の3Dモデルを生成
            tmp_dir, glb_url, glb_key = create_glb_file(input_data=input_data)

            # 成功時のレスポンス
            log.info("処理が正常に完了しました。")

            # レスポンスの構築（どちらの場合もGLB URLを含める）
            return {
                "glb_url": glb_url,  # GLBファイルのURL（S3またはSYNEXA）
                "keys": [glb_key],  # s3上のテクスチャのglbファイル名
            }

        # エラー時のレスポンス（RunPod推奨形式）
        except Exception as e:
            log.error(f"GLB作成時にエラーが発生しました: {str(e)}")
            return {"error": f"GLB作成時にエラーが発生しました: {str(e)}"}

        # 一時ファイルのクリーンアップ
        finally:
            if tmp_dir:
                try:
                    clean(folder_list=[tmp_dir])
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

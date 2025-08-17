import os
import shutil
import sys
import uuid
from types import SimpleNamespace

import torch

# core/triposrディレクトリをパスに追加（tsrモジュールを見つけるため）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core", "triposr"))
# flake8: noqa: E402
import runpod
from runpod import RunPodLogger
from runpod.serverless.utils.rp_cleanup import clean
from triposr import main as triposr_main

from utils.boto3_utils import S3Utils
from utils.env_validator import validate_environment
from utils.glb_utils import extract_texture_from_glb, fetch_glb_from_url
from utils.uuid import generate_uuid

# flake8: noqa: E402

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


def create_3d_model(input_data) -> str:
    """
    ローカルでTripoSRを使用して3Dモデルを生成する

    input_data:
        {
            "image_path": "***.png",
            "prompt": "",  # TripoSRでは使用しないが、互換性のため保持
            "timeout": 300  # TripoSRでは使用しないが、互換性のため保持
        }

    Returns:
        glb_path: 生成されたGLBファイルのパス(uuid/textured_mesh.glb)
    """
    # 入力値を取得
    image_path = input_data.get("image_path")

    # 入力検証
    if not image_path:
        raise ValueError("image_path is required")

    # UUID形式の一時ディレクトリを作成
    output_dir = os.path.join("tmp", str(uuid.uuid4()))
    os.makedirs(output_dir, exist_ok=True)

    # URLの場合は画像をダウンロード
    if image_path.startswith(("http://", "https://")):
        import requests

        # 画像をダウンロード
        response = requests.get(image_path)
        response.raise_for_status()

        # 一時ディレクトリ内に保存
        downloaded_image_path = os.path.join(output_dir, "input_image.png")
        with open(downloaded_image_path, "wb") as f:
            f.write(response.content)
        image_path = downloaded_image_path
        log.info(f"画像をダウンロードしました: {image_path}")

    # CUDAが使用可能か確認
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        log.warn("CPUで処理します")

    try:
        # TripoSR用のパラメータを構築
        args = SimpleNamespace(
            image=[image_path],  # 画像パスのリスト
            device=device,  # 自動選択されたデバイスを使用
            pretrained_model_name_or_path="stabilityai/TripoSR",
            chunk_size=8192,
            mc_resolution=256,
            no_remove_bg=False,  # 背景除去を実行
            foreground_ratio=0.85,
            output_dir=output_dir,
            model_save_format="glb",  # GLB形式で保存
            bake_texture=True,  # テクスチャをベイク
            texture_resolution=1024,  # テクスチャ解像度
            render=False,  # レンダリングは不要
        )

        # TripoSRのメイン処理を実行
        log.info(f"TripoSRで3Dモデルを生成中: {image_path}")
        triposr_main(args)

        # 生成されたGLBファイルを統一された名前にリネーム
        # TripoSRは output_dir/0/mesh.glb に出力する
        original_glb_path = os.path.join(output_dir, "0", "mesh.glb")
        glb_path = os.path.join(output_dir, "textured_mesh.glb")

        if not os.path.exists(original_glb_path):
            raise ValueError(f"GLBファイルが生成されませんでした: {original_glb_path}")

        # ファイルを移動してリネーム
        shutil.move(original_glb_path, glb_path)

        log.info(f"3Dモデル生成完了: {glb_path}")
        return glb_path

    except Exception as e:
        # エラー時は一時ディレクトリを削除（画像ファイルも含まれる）
        if os.path.exists(output_dir):
            clean(folder_list=[output_dir])
        raise e


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

    # サーバ側でGLBファイルからテクスチャを抽出してS3にアップロードする
    elif action == "create":
        tmp_dir = None
        glb_url = None
        glb_path = None

        try:
            # モデル名を取得（デフォルトは外部API）
            model_name = input_data.get("model_name", "triposr")

            if model_name == "triposr":

                # ローカルでTripoSRを使用して3Dモデルを生成
                glb_path = create_3d_model(input_data=input_data)

                # GLBファイルのディレクトリとファイル名を取得
                tmp_dir = os.path.dirname(glb_path)
                glb_filename = os.path.basename(glb_path)

                # GLBファイルをS3にアップロード
                glb_key = generate_uuid(file_extension=".glb")
                glb_url = s3utils.upload_from_server(glb_path, glb_key)
                log.info(f"GLBファイルをS3にアップロードしました: {glb_url}")

            else:
                # 外部APIを使用して3Dモデルを取得
                glb_url = fetch_3d_model(input_data=input_data)

                # URLからglbファイルを取得し、ディレクトリに保存
                tmp_dir, glb_filename = fetch_glb_from_url(glb_url)

            # glbファイルからテクスチャを取り出し、glbファイルと同じ場所にpng形式で保存
            textures_paths = extract_texture_from_glb(
                glb_dir=tmp_dir, glb_filename=glb_filename
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

            # レスポンスの構築（どちらの場合もGLB URLを含める）
            return {
                "glb_url": glb_url,  # GLBファイルのURL（S3またはSYNEXA）
                "textures_url": textures_urls,  # s3上のテクスチャのURL
                "keys": keys,  # s3上のテクスチャのファイル名
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

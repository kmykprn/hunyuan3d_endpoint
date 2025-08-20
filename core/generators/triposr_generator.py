import os
import shutil
import uuid
from types import SimpleNamespace

import torch
from runpod import RunPodLogger
from runpod.serverless.utils.rp_cleanup import clean

# 事前にパッケージをインストールする(以下は手順)
# cd /path/to/hunyuan3d_endpoint/core/triposr
# pip install -e .
from triposr import main as triposr_main

log = RunPodLogger()


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
    use_texture = input_data.get("use_texture", True)

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
            bake_texture=use_texture,  # use_textureパラメータと連動
            texture_resolution=1024,  # テクスチャ解像度
            render=False,  # レンダリングは不要
        )

        # TripoSRのメイン処理を実行
        log.info(f"TripoSRで3Dモデルを生成中: {image_path}")
        log.info(f"テクスチャ生成: {use_texture}")
        triposr_main(args)

        # ファイル名を決定
        if use_texture:
            glb_filename = "textured_mesh.glb"
        else:
            glb_filename = "mesh.glb"

        # 生成されたGLBファイルを統一された名前にリネーム
        original_glb_path = os.path.join(output_dir, "0", "mesh.glb")
        if not os.path.exists(original_glb_path):
            raise ValueError(f"GLBファイルが生成されませんでした: {original_glb_path}")

        # uuid/{textured_}mesh.glb にファイルを移動
        glb_path = os.path.join(output_dir, glb_filename)
        shutil.move(original_glb_path, glb_path)

        log.info(f"3Dモデル生成完了: {glb_path}")
        return glb_path

    except Exception as e:
        # エラー時は一時ディレクトリを削除（画像ファイルも含まれる）
        if os.path.exists(output_dir):
            clean(folder_list=[output_dir])
        raise e
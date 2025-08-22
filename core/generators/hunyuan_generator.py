import os
import uuid
from PIL import Image
from runpod import RunPodLogger

# 事前にパッケージをインストールする(以下は手順)
# cd /path/to/hunyuan3d_endpoint/core/Hunyuan3D-2
# pip install -e .
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
from hy3dgen.texgen import Hunyuan3DPaintPipeline

log = RunPodLogger()

# グローバルでモデルを保持（遅延初期化）
_pipeline_shapegen = None
_pipeline_texgen = None


def create_3d_model_hunyuan(input_data) -> str:
    """
    ローカルのHunyuan3D-2モデルを使用して3Dモデルを生成

    Args:
        input_data: {
            "image_path": "画像ファイルパス（S3 URLまたはローカル）",
            "prompt": "テキストプロンプト（オプション）",
            "use_texture": True/False（テクスチャ生成の有無、デフォルトTrue）
        }

    Returns:
        glb_path: 生成されたGLBファイルのローカルパス
    """
    global _pipeline_shapegen, _pipeline_texgen
    
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
   
    # 3Dモデルとテクスチャを生成
    try:
        # 3Dモデルを生成
        if _pipeline_shapegen is None:
            log.info("Hunyuan3D-2モデルを初期化中...")
            _pipeline_shapegen = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
                model_path = 'tencent/Hunyuan3D-2mini',
                subfolder='hunyuan3d-dit-v2-mini-fast'
            )
            log.info("Hunyuan3D-2モデルの初期化完了")
        mesh = _pipeline_shapegen(image=image_path)[0]
        glb_filename = "mesh.glb"
        
        # （オプション）テクスチャを生成
        use_texture = input_data.get("use_texture", True)
        if use_texture:
            if _pipeline_texgen is None:
                log.info("Hunyuan3D-2テクスチャ生成モデルを初期化中...")
                _pipeline_texgen = Hunyuan3DPaintPipeline.from_pretrained('tencent/Hunyuan3D-2')
                log.info("Hunyuan3D-2テクスチャ生成モデルの初期化完了")
            mesh = _pipeline_texgen(mesh, image=image_path)
            glb_filename = "textured_" + glb_filename

        # 5. GLBファイルとして保存
        glb_path = os.path.join(output_dir, glb_filename)
        mesh.export(glb_path)
        log.info(f"3Dモデル生成完了: {glb_path}")

        return glb_path

    except Exception as e:
        # エラー時は一時ディレクトリを削除（画像ファイルも含まれる）
        if os.path.exists(output_dir):
            from runpod.serverless.utils.rp_cleanup import clean
            clean(folder_list=[output_dir])
        raise e
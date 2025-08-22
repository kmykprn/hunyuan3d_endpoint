import os
import uuid
import gc
import torch
import psutil
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


def get_memory_info():
    """メモリ使用状況を取得"""
    # CPU メモリ情報
    process = psutil.Process()
    cpu_memory = process.memory_info().rss / 1024 / 1024 / 1024  # GB
    
    # GPU メモリ情報
    gpu_info = {}
    if torch.cuda.is_available():
        gpu_info = {
            'allocated': torch.cuda.memory_allocated() / 1024 / 1024 / 1024,  # GB
            'reserved': torch.cuda.memory_reserved() / 1024 / 1024 / 1024,  # GB
            'max_memory': torch.cuda.max_memory_allocated() / 1024 / 1024 / 1024,  # GB
        }
    
    return {
        'cpu_memory_gb': round(cpu_memory, 2),
        'gpu_allocated_gb': round(gpu_info.get('allocated', 0), 2),
        'gpu_reserved_gb': round(gpu_info.get('reserved', 0), 2),
        'gpu_max_gb': round(gpu_info.get('max_memory', 0), 2),
    }


def create_3d_model_hunyuan(input_data) -> str:
    """
    ローカルのHunyuan3D-2モデルを使用して3Dモデルを生成

    Args:
        input_data: {
            "image_path": "画像ファイルパス（S3 URLまたはローカル）",
            "prompt": "テキストプロンプト（オプション）",
            "use_texture": True/False（テクスチャ生成の有無、デフォルトTrue）,
            "num_inference_steps": int（推論ステップ数、デフォルト25）,
            "octree_resolution": int（オクツリー解像度、デフォルト256）,
            "num_chunks": int（チャンク数、デフォルト4000）,
            "texture_render_size": int（テクスチャレンダリングサイズ、デフォルト1024）,
            "texture_size": int（テクスチャサイズ、デフォルト1024）
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
        # 初期メモリ状態
        log.info(f"[初期] メモリ状態: {get_memory_info()}")
        
        # 3Dモデルを生成
        if _pipeline_shapegen is None:
            log.info("Hunyuan3D-2モデルを初期化中...")
            _pipeline_shapegen = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
                model_path = 'tencent/Hunyuan3D-2mini',
                subfolder='hunyuan3d-dit-v2-mini-fast'
            )
            log.info("Hunyuan3D-2モデルの初期化完了")
            log.info(f"[形状モデルロード後] メモリ状態: {get_memory_info()}")
        # パラメータを取得（デフォルト値付き）
        num_inference_steps = input_data.get("num_inference_steps", 25)
        octree_resolution = input_data.get("octree_resolution", 256)
        num_chunks = input_data.get("num_chunks", 4000)
        
        log.info(f"3Dモデル生成パラメータ: steps={num_inference_steps}, resolution={octree_resolution}, chunks={num_chunks}")
        
        mesh = _pipeline_shapegen(
            image=image_path,
            num_inference_steps=num_inference_steps,
            octree_resolution=octree_resolution,
            num_chunks=num_chunks,
        )[0]
        glb_filename = "mesh.glb"
        log.info(f"[形状生成後] メモリ状態: {get_memory_info()}")
        
        # （オプション）テクスチャを生成
        use_texture = input_data.get("use_texture", True)
        
        if use_texture:
            # テクスチャ生成を行う場合、形状生成モデルのメモリを解放
            log.info("形状生成モデルのメモリを解放中...")
            _pipeline_shapegen = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            log.info("メモリ解放完了")
            log.info(f"[形状モデル解放後] メモリ状態: {get_memory_info()}")
            
            # テクスチャを生成
            if _pipeline_texgen is None:
                log.info("Hunyuan3D-2テクスチャ生成モデルを初期化中...")
                _pipeline_texgen = Hunyuan3DPaintPipeline.from_pretrained('tencent/Hunyuan3D-2', subfolder='hunyuan3d-paint-v2-0-turbo')
                log.info("Hunyuan3D-2テクスチャ生成モデルの初期化完了")
                log.info(f"[テクスチャモデルロード後] メモリ状態: {get_memory_info()}")
            
            # テクスチャパラメータを取得（デフォルト値付き）
            texture_render_size = input_data.get("texture_render_size", 1024)
            texture_size = input_data.get("texture_size", 1024)
            
            _pipeline_texgen.config.render_size = texture_render_size
            _pipeline_texgen.config.texture_size = texture_size
            
            log.info(f"テクスチャ生成パラメータ: render_size={texture_render_size}, texture_size={texture_size}")
            log.info("テクスチャ付3Dモデルを作成開始")
            mesh = _pipeline_texgen(mesh, image=image_path)
            log.info("テクスチャ付3Dモデル作成完了")
            log.info(f"[テクスチャ生成後] メモリ状態: {get_memory_info()}")
            glb_filename = "textured_mesh.glb"
            
            # テクスチャ生成モデルのメモリを解放
            log.info("テクスチャ生成モデルのメモリを解放中...")
            _pipeline_texgen = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            log.info("メモリ解放完了")
            log.info(f"[テクスチャモデル解放後] メモリ状態: {get_memory_info()}")

        # 5. GLBファイルとして保存
        glb_path = os.path.join(output_dir, glb_filename)
        mesh.export(glb_path)
        log.info(f"3Dモデル生成完了: {glb_path}")
        log.info(f"[最終] メモリ状態: {get_memory_info()}")

        return glb_path

    except Exception as e:
        # エラー時は一時ディレクトリを削除（画像ファイルも含まれる）
        if os.path.exists(output_dir):
            from runpod.serverless.utils.rp_cleanup import clean
            clean(folder_list=[output_dir])
        raise e
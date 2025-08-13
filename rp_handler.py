import os
import runpod
from runpod.serverless.utils.rp_cleanup import clean
from utils.glb_utils import fetch_glb_from_url, extract_texture_from_glb, encode_textures_to_base64

# ローカル開発環境でのみdotenvを使用
if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()

# ローカル実行時は.envからAPIキーを取得
# runpod実行時はsecretからAPIキーを取得
api_key = os.getenv('SYNEXA_API_KEY')

# APIキーの存在確認
if not api_key:
    raise ValueError("SYNEXA_API_KEY not found in environment variables")


import synexa
client = synexa.Synexa(api_key=api_key)


def handler(event):
    """
    外部APIから3Dモデルを取得する
    
    input:
        "input": {
            "image_path": "***.png",
            "prompt": "",
            "timeout": 300
        }
    
    Returns:
        成功時: {"glb_url": str, "textures": list}
        エラー時: {"error": str}
    """
    glb_dir = None
    
    try:
        # 入力値を取得
        input_data = event['input']
        image_path = input_data.get('image_path')
        prompt = input_data.get('prompt', '')
        timeout = input_data.get('timeout', 300)
        
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
                "octree_resolution": "256"
            },
            wait=timeout
        )
        
        # GLBファイルURLを取得
        textured_glb_file_url = None
        for f in output:
            if 'textured_mesh' in f.url:
                textured_glb_file_url = f.url
                break
        
        if not textured_glb_file_url:
            raise ValueError("No textured mesh found in API response")
        
        # URLからglbファイルを保存し、出力先ディレクトリとファイル名を取得する
        glb_dir, glb_filename = fetch_glb_from_url(textured_glb_file_url)
        
        # glbファイルからテクスチャをpngで保存
        texture_paths = extract_texture_from_glb(glb_dir=glb_dir, glb_filename=glb_filename)
        
        # テクスチャをBase64エンコード
        textures = encode_textures_to_base64(texture_paths)
        
        # 成功時のレスポンス
        return {
            "glb_url": textured_glb_file_url,
            "textures": textures
        }
        
    except Exception as e:
        # エラー時のレスポンス（RunPod推奨形式）
        return {
            "error": str(e)
        }
    
    finally:
        # 一時ファイルのクリーンアップ
        if glb_dir:
            try:
                clean(folder_list=[glb_dir])
            except:
                # クリーンアップの失敗は無視
                pass

if __name__ == '__main__':
    runpod.serverless.start({'handler': handler })
import os
import runpod
from runpod import RunPodLogger
from pipeline.postprocess import postprocess
from utils.s3_utlis import remove_textures_file
from runpod.serverless.utils.rp_cleanup import clean

log = RunPodLogger()

# ローカル開発環境でのみdotenvを使用
if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()

# ローカル実行時は.envからAPIキーを取得し、runpod実行時はsecretからAPIキーを取得
api_key = os.getenv('SYNEXA_API_KEY')

# APIキーの存在確認
if not api_key:
    raise ValueError("SYNEXA_API_KEY not found in environment variables")


import synexa
client = synexa.Synexa(api_key=api_key)


def create_3d_model(input_data):
    """
    外部APIから3Dモデルを取得する
    
    input_data:
        {
            "image_path": "***.png",
            "prompt": "",
            "timeout": 300
        }
    
    Returns:
        成功時: {"glb_url": str, "textures": list}
        エラー時: {"error": str}
    """

    # 入力値を取得
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
    glb_url = None
    for f in output:
        if 'textured_mesh' in f.url:
            glb_url = f.url
            break
    
    if not glb_url:
        raise ValueError("No textured mesh found in API response")

    # GLBファイルをダウンロードし、GLBファイル内のテクスチャをAWS S3に保存する
    tmp_dir, textures_url = postprocess(glb_url)
    
    return tmp_dir, glb_url, textures_url
    

def handler(event):
    input_data = event['input']
    action = input_data['action']
    
    if action == "create":
        tmp_dir = None
        try:
            tmp_dir, glb_url, textures_url = create_3d_model(input_data=input_data)

            # 成功時のレスポンス
            return {
                "glb_url": glb_url,
                "textures_url": textures_url
            }
        
        except Exception as e:
            # エラー時のレスポンス（RunPod推奨形式）
            return {
                "error": str(e)
            }

        finally:
            # 一時ファイルのクリーンアップ
            if tmp_dir:
                try:
                    clean(folder_list=[tmp_dir])
                except:
                    # クリーンアップの失敗は無視
                    pass
    
    elif action == "delete":
        # 指定されたS3のファイルを削除する
        try:
            url_list = input_data.get('urls', [])
            remove_textures_file(url_list=url_list)
            return {"status": "success", "deleted_urls": url_list}
        except Exception as e:
            return {
                "error": str(e)
            }
    else:
        return {"error": f"Unknown action: {action}"} 


if __name__ == '__main__':
    runpod.serverless.start({'handler': handler })
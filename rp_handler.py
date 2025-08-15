import os
import runpod
from runpod import RunPodLogger
from runpod.serverless.utils.rp_cleanup import clean
from utils.boto3_upload_file import s3_file_upload
from utils.boto3_delete_file import s3_delete_from_url
from utils.glb_utils import fetch_glb_from_url, extract_texture_from_glb

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
    
    # GLBファイルURLを返却
    glb_url = None
    for f in output:
        if 'textured_mesh' in f.url:
            glb_url = f.url
            return glb_url
    
    # GLBファイルURLが見つからない場合は異常終了
    if not glb_url:
        log.error("テクスチャ付メッシュ生成のAPIに失敗しました")
        raise ValueError("No textured mesh found in API response")
    
    return ""


def handler(event):
    log.info("ジョブを受信しました。")

    input_data = event['input']
    action = input_data['action']
    
    if action == "create":
        glb_dir = None
        try:
            # glbファイルのurlを取得
            glb_url = fetch_3d_model(input_data=input_data)
            
            # URLからglbファイルを取得し、ディレクトリに保存
            glb_dir, glb_filename = fetch_glb_from_url(glb_url)
            
            # glbファイルからテクスチャを取り出し、glbファイルと同じ場所にpng形式で保存
            textures_paths = extract_texture_from_glb(glb_dir=glb_dir, glb_filename=glb_filename)

            # テクスチャファイルをs3にアップロードし、ダウンロード用urlを取得
            textures_urls = []
            for path in textures_paths:
                url = s3_file_upload(path)
                if url is None:
                    raise Exception(f"S3へのアップロードに失敗しました: {path}")
                textures_urls.append(url)

            # 成功時のレスポンス
            log.info("処理が正常に完了しました。")
            return {
                "status": "success",
                "glb_url": glb_url,
                "textures_url": textures_urls
            }
        
        except Exception as e:
            # エラー時のレスポンス（RunPod推奨形式）
            log.error(f"エラーが発生しました: {str(e)}")
            return {"status": "error", "message": str(e)}

        finally:
            # 一時ファイルのクリーンアップ
            if glb_dir:
                try:
                    clean(folder_list=[glb_dir])
                    log.info("ファイル削除が正常に完了しました。")
                except:
                    # クリーンアップの失敗は無視
                    log.error(f"エラーが発生しました: {str(e)}")
                    pass

    elif action == "delete":
        
        try:
            # 送信されてきたurlのファイルを削除
            all_deleted = True
            for url in input_data['urls']:
                if not s3_delete_from_url(url):
                    all_deleted = False
                    log.error(f"ファイル削除に失敗しました: {url}")
            
            if all_deleted:
                return {"status": "success", "message": "すべてのファイルが削除されました"}
            else:
                return {"status": "error", "message": "一部のファイルの削除に失敗しました"}
        
        except Exception as e:
            log.error(f"ファイル削除処理でエラーが発生しました：{e}")
            return {"status": "error", "message": str(e)}


if __name__ == '__main__':
    runpod.serverless.start({'handler': handler })
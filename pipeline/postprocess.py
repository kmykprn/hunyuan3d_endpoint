from runpod import RunPodLogger
from utils.s3_utlis import upload_textures_s3
from utils.glb_utils import fetch_glb_from_url, extract_texture_from_glb

log = RunPodLogger()

def postprocess(glb_url: str):
    """
    GLBファイルをダウンロードし、GLBファイル内のテクスチャをAWS S3に保存する
    
    Args:
        glb_url: GLBファイルのURL
    
    Returns:
        textures_url: テクスチャ群のurl
        glb_dir: glbファイルの一時出力先ディレクトリ
    """
    try:
        # URLからglbファイルを保存し、一時出力先ディレクトリとファイル名を取得する
        tmp_dir, glb_filename = fetch_glb_from_url(glb_url)
        
        # glbファイルからテクスチャをpngで保存(戻り値：テクスチャのファイルパス)
        textures_path = extract_texture_from_glb(glb_dir=tmp_dir, glb_filename=glb_filename)
        
        # テクスチャをs3に保存し、テクスチャのurlを取得。
        # job_idとしてGLBファイルの格納先ディレクトリ名（UUID4）を指定。
        textures_url = upload_textures_s3(job_id=tmp_dir, textures_path=textures_path)

        return tmp_dir, textures_url

    except Exception as e:
        log.error(f"テクスチャを抽出・保存中にエラー: {e}")
        raise e
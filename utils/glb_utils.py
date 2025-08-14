import os
import urllib.request
import glob
import base64
from pygltflib import GLTF2
from pygltflib.utils import ImageFormat


def fetch_glb_from_url(url: str) -> tuple[str, str]:
    """
    urlからglbファイルをダウンロードし、格納する
    
    Args:
        url: GLBファイルが保存されているURL
    
    Returns:
        (output_dir, filename): (glbファイルの一時出力先ディレクトリ, 保存ファイル名)
    """
    
    # urlからファイル名のみ取得（例. 'e9d16206-de03-4dbc-97d7-6a17c4c86e1e_textured_mesh.glb'
    file_base_name = os.path.basename(url)

    # ファイル名をディレクトリ名とファイル名に分解
    # 例. dir_path='e9d16206-de03-4dbc-97d7-6a17c4c86e1e', filename='textured_mesh.glb'
    output_dir, filename = file_base_name.split('_', 1)
    
    # 出力先ディレクトリを作成し、GLBファイルを保存
    os.makedirs(output_dir, exist_ok=True)
    glb_file_uri = os.path.join(output_dir, filename)       
    urllib.request.urlretrieve(url, glb_file_uri)
    
    return (output_dir, filename)


def extract_texture_from_glb(glb_dir: str, glb_filename: str) -> list[str]:
    """
    指定されたglbファイル名から、テクスチャを抽出して返す
    
    Args:
        glb_dir: glbファイルが保存されているディレクトリ
        glb_filename: glbファイルのファイル名（ファイル名のみ）
    
    Returns:
        textures_path: テクスチャのパス（list）
    """
    # glbファイルの絶対パスを取得
    glb_file_path = os.path.join(glb_dir, glb_filename)
    
    # glbファイルを取得し、テクスチャを同じディレクトリに保存
    gltf = GLTF2().load(glb_file_path)
    gltf.convert_images(ImageFormat.FILE)
    
    # テクスチャのパスを取得
    textures_path = glob.glob(os.path.join(glb_dir, '*.png'))
    return textures_path
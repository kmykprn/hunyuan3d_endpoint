import os
from runpod import RunPodLogger
from dotenv import load_dotenv

log = RunPodLogger()

def get_synexa_client():
    
    # ローカル開発環境でのみdotenvを使用
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        
    import synexa # flake8: noqa: E402

    # 環境変数取得
    api_key = os.getenv("SYNEXA_API_KEY")

    # Synexaクライアントの初期化
    client = synexa.Synexa(api_key=api_key)
    
    return client


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
    client = get_synexa_client()
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
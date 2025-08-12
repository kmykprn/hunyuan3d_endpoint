import runpod
import os

# ローカル実行時は.envからAPIキーを取得
# runpod実行時はsecretからAPIキーを取得
api_key = os.getenv('SYNEXA_API_KEY')

# APIキーの存在確認
if not api_key:
    raise ValueError("SYNEXA_API_KEY not found in environment variables")


import synexa
client = synexa.Synexa(api_key=api_key)


def get_hunyuan3d_model(input):
    """
    外部APIから3Dモデルを取得する
    
    input:
        "input": {
            "image_path": "***.png",
            "prompt": "",
            "timeout": 300
        }
    
    Returns：
    [
        FileOutput(url='https://***_white_mesh.glb',
        _client=<httpx.Client object at ***>),
        FileOutput(url='https://***_textured_mesh.glb',
        _client=<httpx.Client object at ***>)
    ]
    """

    image_path = input.get('image_path')
    prompt = input.get('prompt')
    timeout = input.get('timeout')

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
    
    return output


def postprocess_asset(asset):
    """
    glbファイル本体と、テクスチャのpngを取得
    """
    glb = asset
    return glb

def handler(event):
    
    runpod_input = event['input']
    
    # 3dモデルを作成
    asset = get_hunyuan3d_model(runpod_input)
    
    # 後処理
    output = asset
    
    return output


if __name__ == '__main__':
    runpod.serverless.start({'handler': handler })
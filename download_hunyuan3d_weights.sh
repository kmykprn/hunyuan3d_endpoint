# プロジェクトルートにmodelsディレクトリ作成
mkdir -p models

# Pythonスクリプトでダウンロード
python3 -c "
from huggingface_hub import snapshot_download
path1 = snapshot_download('tencent/Hunyuan3D-2mini', allow_patterns=['hunyuan3d-dit-v2-mini-fast/*'], cache_dir='./models')
path2 = snapshot_download('tencent/Hunyuan3D-2.1', allow_patterns=['hunyuan3d-paintpbr-v2-1/*'], cache_dir='./models')
path3 = snapshot_download('tencent/Hunyuan3D-2', allow_patterns=['hunyuan3d-paint-v2-0/*'], cache_dir='./models')
path4 = snapshot_download('tencent/Hunyuan3D-2', allow_patterns=['hunyuan3d-paint-v2-0-turbo/*'], cache_dir='./models')
path5 = snapshot_download('tencent/Hunyuan3D-2', allow_patterns=['hunyuan3d-delight-v2-0/*'], cache_dir='./models')
print('Downloaded to:', path1, path2, path3, path4, path5)
"
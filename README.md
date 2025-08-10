# hunyuan3d_endpoint
hunyuan3dのRunpod向けレポジトリ



## はじめに
これはRunpodの最小限のサンプルです。
このコードにより、Docker imageをサーバレスエンドポイントにデプロイすることができます。エンドポイントにリクエストが到達すると、ワーカーが起動し、rp_handler.pyに記載されているコードが実行されます。


実行方法
# 1. Pythonの仮想環境を作成する
python3 -m venv .venv

# 2. 仮想環境を起動する
## On macOS/Linux:
source .venv/bin/activate

## On Windows:
.venv\Scripts\activate

# 3. RunPod SDK をインストールする
pip install runpod

# 4. スクリプトをローカルで実行する
スクリプトは、自動的に test_input.json を入力として読み込み、 handler関数にイベントとして渡します。

python3 rp_handler.py

# Docker imageをビルドする
docker build -t your-dockerhub-username/your-image-name:v1.0.0 --platform linux/amd64 .

# docker hubにイメージをpushする
docker push your-dockerhub-username/your-image-name:v1.0.0
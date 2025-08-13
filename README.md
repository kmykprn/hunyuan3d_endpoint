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

# 3. 依存関係 をインストールする
pip install -r requirements.txt

# 4. スクリプトをローカルで実行する
python3 rp_handler.py

# 5. Githubからワーカーをデプロイする
Runpod の GitHub 統合の仕組みを使用し、GithubからコードとDockerfileを取得して、コンテナイメージを構築し、Runpodのコンテナレジストリに保存して、エンドポイントにデプロイします。

詳細は[こちら](https://docs.runpod.io/serverless/workers/github-integration)

# Docker imageをビルドする
docker build -t your-dockerhub-username/your-image-name:v1.0.0 --platform linux/amd64 .

# docker hubにイメージをpushする
docker push your-dockerhub-username/your-image-name:v1.0.0
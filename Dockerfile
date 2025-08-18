# python:3.10-slim
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel

WORKDIR /

RUN pip install --upgrade setuptools

# システムパッケージをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libosmesa6-dev \
    libglu1-mesa-dev \
    libglib2.0-0 \
    libgomp1 \
    wget \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# パッケージをインストール
COPY requirements.txt /requirements.txt
RUN pip install -r requirements.txt

COPY core/triposr/ /core/triposr/
RUN pip install -r /core/triposr/requirements.txt

# モデルファイルを事前にダウンロード
# rembgのu2netモデルをダウンロード
RUN mkdir -p /root/.u2net && \
    wget -q --show-progress --progress=bar:force:noscroll \
    https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx \
    -O /root/.u2net/u2net.onnx

# TripoSRのモデルファイルをダウンロード
# Hugging Faceのキャッシュディレクトリ構造を作成
RUN mkdir -p /root/.cache/huggingface/hub/models--stabilityai--TripoSR/snapshots/5b521936b01fbe1890f6f9baed0254ab6351c04a && \
    mkdir -p /root/.cache/huggingface/hub/models--stabilityai--TripoSR/blobs && \
    # config.yamlをダウンロード
    wget -q --show-progress --progress=bar:force:noscroll \
    https://huggingface.co/stabilityai/TripoSR/resolve/main/config.yaml \
    -O /root/.cache/huggingface/hub/models--stabilityai--TripoSR/snapshots/5b521936b01fbe1890f6f9baed0254ab6351c04a/config.yaml && \
    # model.ckptをダウンロード
    wget -q --show-progress --progress=bar:force:noscroll \
    https://huggingface.co/stabilityai/TripoSR/resolve/main/model.ckpt \
    -O /root/.cache/huggingface/hub/models--stabilityai--TripoSR/snapshots/5b521936b01fbe1890f6f9baed0254ab6351c04a/model.ckpt

# 必要な素材をコピー
COPY rp_handler.py /rp_handler.py
COPY utils/ /utils/

# 仮想ディスプレイサーバーを起動
RUN echo '#!/bin/bash\n\
# Xvfbを背景で起動\n\
Xvfb :99 -screen 0 1024x768x24 &\n\
export DISPLAY=:99\n\
# 少し待ってからコマンド実行\n\
sleep 2\n\
exec "$@"' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

ENV CUDA_VISIBLE_DEVICES=0
ENV MESA_GL_VERSION_OVERRIDE=3.3
ENV MESA_GLSL_VERSION_OVERRIDE=330
ENV PYOPENGL_PLATFORM=osmesa
ENV DISPLAY=:99

# コンテナ起動時に仮想サーバーを起動
ENTRYPOINT ["/entrypoint.sh"]

# コンテナで実行するコマンドを指定
CMD ["python3", "-u", "rp_handler.py"]
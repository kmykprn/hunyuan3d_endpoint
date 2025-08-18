# python:3.10-slim
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel

WORKDIR /

RUN pip install --upgrade setuptools

# システムパッケージをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libgl1-mesa-glx \
    xvfb \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# pytorchをインストール
RUN pip install torch==2.5.1 torchvision --index-url https://download.pytorch.org/whl/cu124

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

ENV CUDA_VISIBLE_DEVICES=0

# Start the container
CMD ["python3", "-u", "rp_handler.py"]
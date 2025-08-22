# ================= Stage 1: 基本環境 =================
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel as base

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


# ================= Stage 2: Python依存関係 =================
FROM base as dependencies

# パッケージをインストール
COPY requirements.txt /requirements.txt
RUN pip install -r requirements.txt

# ================= Stage 3: Hunyuan3Dとパッケージをインストール =================
FROM dependencies as hunyuan3d_base

ENV TORCH_CUDA_ARCH_LIST="7.5;8.0;8.6;8.9;9.0"
ENV FORCE_CUDA="1"
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=/usr/local/cuda/bin:$PATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# core/Hunyuan3D-2をコピーしてパッケージとしてインストール
COPY core/Hunyuan3D-2/ /core/Hunyuan3D-2/

RUN pip install -e /core/Hunyuan3D-2/ && \
    cd /core/Hunyuan3D-2/hy3dgen/texgen/custom_rasterizer && \
    pip install . && \
    cd /core/Hunyuan3D-2/hy3dgen/texgen/differentiable_renderer && \
    pip install .

# ================= Stage 7: 最終イメージ =================
FROM hunyuan3d_base as final

# 必要な素材をコピー
COPY rp_handler.py /rp_handler.py
COPY utils/ /utils/
COPY core/generators/ /core/generators/

ENV CUDA_VISIBLE_DEVICES=0
ENV PYTHONPATH="/core/Hunyuan3D-2:/core/generators:$PYTHONPATH"
ENV HY3DGEN_MODELS=/runpod-volume/models
ENV HUGGINGFACE_HUB_CACHE=/runpod-volume/models/

# コンテナで実行するコマンドを指定
CMD ["python3", "-u", "rp_handler.py"]
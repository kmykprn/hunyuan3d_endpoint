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

# ================= Stage 3: TripoSRとパッケージ =================
FROM dependencies as models_triposr

# core/triposrをコピーしてパッケージとしてインストール
COPY core/triposr/ /core/triposr/
RUN pip install -r /core/triposr/requirements.txt && \
    pip install -e /core/triposr/

# core/generatorsをコピー
COPY core/generators/ /core/generators/

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


# ================= Stage 4: Hunyuan3Dとパッケージ =================
FROM models_triposr as models_triposr_hunyuan3d

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


# ================= Stage 5: Hunyuan3DのDitの重み =================
FROM models_triposr_hunyuan3d as models_triposr_hunyuan3d_dit

# Hunyuan3D-2のモデルを事前ダウンロード
RUN CUDA_VISIBLE_DEVICES="" python3 -c "\
from huggingface_hub import snapshot_download; \
print('Downloading model files only...'); \
path = snapshot_download('tencent/Hunyuan3D-2mini', allow_patterns=['hunyuan3d-dit-v2-mini-fast/*']); \
print('Downloaded to:', path)" && \
    mkdir -p /root/.cache/hy3dgen/tencent && \
    ln -sf /root/.cache/huggingface/hub/models--tencent--Hunyuan3D-2/snapshots/* \
           /root/.cache/hy3dgen/tencent/Hunyuan3D-2 && \
    echo "Model files prepared for runtime loading"

# ================= Stage 6: Hunyuan3Dの重み =================
FROM models_triposr_hunyuan3d_dit as models_triposr_hunyuan3d_dit_texture

# Hunyuan3D-2のテクスチャモデルを事前ダウンロード
RUN CUDA_VISIBLE_DEVICES="" python3 -c "\
from huggingface_hub import snapshot_download; \
print('Downloading texture model files only...'); \
path = snapshot_download('tencent/Hunyuan3D-2'); \
print('Downloaded to:', path)" && \
    mkdir -p /root/.cache/hy3dgen/tencent && \
    ln -sf /root/.cache/huggingface/hub/models--tencent--Hunyuan3D-2/snapshots/* \
           /root/.cache/hy3dgen/tencent/Hunyuan3D-2 && \
    echo "Texture model files prepared for runtime loading"

# ================= Stage 7: 最終イメージ =================
FROM models_triposr_hunyuan3d_dit_texture as final

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
ENV PYTHONPATH="/core/triposr:/core/Hunyuan3D-2:/core/generators:$PYTHONPATH"

# コンテナ起動時に仮想サーバーを起動
ENTRYPOINT ["/entrypoint.sh"]

# コンテナで実行するコマンドを指定
CMD ["python3", "-u", "rp_handler.py"]
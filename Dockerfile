# python:3.10-slim
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel

WORKDIR /

RUN pip install --upgrade setuptools

# システムパッケージをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# pytorchをインストール
RUN pip install torch==2.5.1 torchvision --index-url https://download.pytorch.org/whl/cu124

# パッケージをインストール
COPY requirements.txt /requirements.txt
RUN pip install -r requirements.txt

COPY core/triposr/ /core/triposr/
RUN pip install -r /core/triposr/requirements.txt

# 必要な素材をコピー
COPY rp_handler.py /rp_handler.py
COPY utils/ /utils/

# Start the container
CMD ["python3", "-u", "rp_handler.py"]
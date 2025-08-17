FROM python:3.10-slim

WORKDIR /

RUN pip install --upgrade setuptools

# pytorchをインストール
RUN pip install torch==2.5.1 torchvision --index-url https://download.pytorch.org/whl/cu124

# コピー
COPY 3dcore/triposr/ /3dcore/triposr/
COPY requirements.txt /requirements.txt
COPY rp_handler.py /rp_handler.py
COPY utils/ /utils/

# パッケージをインストール
RUN pip install -r requirements.txt
RUN pip install -r 3dcore/triposr/requirements.txt

# Start the container
CMD ["python3", "-u", "rp_handler.py"]
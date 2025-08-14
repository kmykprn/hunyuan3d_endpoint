FROM python:3.10-slim

WORKDIR /
COPY requirements.txt /requirements.txt
RUN pip install -r requirements.txt
COPY rp_handler.py /rp_handler.py
COPY utils/ /utils/
COPY pipeline/ /pipeline/

# Start the container
CMD ["python3", "-u", "rp_handler.py"]
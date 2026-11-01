FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    # Remove torch dirs safe to delete (tests, C++ headers, benchmarks)
    rm -rf /usr/local/lib/python3.11/site-packages/torch/test \
    /usr/local/lib/python3.11/site-packages/torch/benchmarks \
    /usr/local/lib/python3.11/site-packages/torch/include \
    /usr/local/lib/python3.11/site-packages/torch/share \
    && \
    # Remove packages not needed at runtime
    rm -rf /usr/local/lib/python3.11/site-packages/networkx \
    /usr/local/lib/python3.11/site-packages/pygments \
    /usr/local/lib/python3.11/site-packages/pip \
    /usr/local/lib/python3.11/site-packages/setuptools \
    && \
    rm -rf /tmp/* /root/.cache

COPY . /app
EXPOSE 8000
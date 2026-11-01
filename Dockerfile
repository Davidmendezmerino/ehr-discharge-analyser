FROM python:3.11-slim

WORKDIR /app

# Install all dependencies in one layer
COPY app/api/requirements.txt /tmp/api-requirements.txt
COPY app/ui/requirements.txt /tmp/ui-requirements.txt

RUN pip install --no-cache-dir \
    -r /tmp/api-requirements.txt \
    -r /tmp/ui-requirements.txt && \
    # Remove unused packages to save space
    rm -rf /usr/local/lib/python3.11/site-packages/torch/test \
    /usr/local/lib/python3.11/site-packages/torch/benchmarks \
    /usr/local/lib/python3.11/site-packages/torch/include \
    /usr/local/lib/python3.11/site-packages/torch/share \
    /usr/local/lib/python3.11/site-packages/networkx \
    /usr/local/lib/python3.11/site-packages/pygments \
    /usr/local/lib/python3.11/site-packages/pip \
    /usr/local/lib/python3.11/site-packages/setuptools \
    && \
    rm -rf /tmp/* /root/.cache

# Copy API code
COPY app/api/main.py /app/api/main.py
COPY app/api/ml/ /app/api/ml/
COPY app/api/models/ /app/api/models/
COPY app/api/services/ /app/api/services/

# Copy UI code
COPY app/ui/app.py /app/ui/app.py
COPY app/ui/.streamlit/ /app/ui/.streamlit/

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# HuggingFace Spaces requires port 7860
EXPOSE 7860

CMD ["/app/start.sh"]

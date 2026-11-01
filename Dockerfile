FROM python:3.11-slim

WORKDIR /app

# Install all dependencies in one layer
COPY app/api/requirements.txt /tmp/api-requirements.txt
COPY app/ui/requirements.txt /tmp/ui-requirements.txt

RUN pip install --no-cache-dir \
    -r /tmp/api-requirements.txt \
    -r /tmp/ui-requirements.txt

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

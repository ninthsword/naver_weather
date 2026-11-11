FROM mcr.microsoft.com/playwright/python:v1.65.0-noble@sha256:f9294526294a7bdfb8ca8aa7d815c049125a10e73b65d47fb9a80f5d74f284a6

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes --break-system-packages -r requirements.txt
COPY naver_render.py .
USER pwuser
EXPOSE 8765
CMD ["python3", "-B", "naver_render.py"]

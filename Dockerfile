FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg imagemagick git fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
COPY --chown=user requirements.txt requirements-security.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements-security.txt || pip install --no-cache-dir -r requirements.txt
COPY --chown=user . .
USER user
ENV PYTHONPATH=/home/user/app HOME=/home/user PYTHONUNBUFFERED=1
EXPOSE 7860
CMD python scripts/make_config.py && exec streamlit run webui/Main.py --server.address=0.0.0.0 --server.port=7860 \
    --server.enableXsrfProtection=false --server.enableCORS=false

FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# Python 3.10 (version par defaut d'Ubuntu 22.04, dispo sans depot tiers)
# + libs requises par opencv (dependance d'insightface) et Pillow.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-dev \
    python3-pip \
    libjpeg62-dev \
    zlib1g-dev \
    libgl1 \
    libglib2.0-0 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
# insightface tire "onnxruntime" (CPU) comme dependance transitive ; comme il
# partage le meme namespace de package que "onnxruntime-gpu", l'installation
# la plus recente ecrase l'autre sur disque, et pip ne garantit pas l'ordre
# d'installation entre paquets d'un meme `pip install -r`. On force donc
# onnxruntime-gpu en dernier pour etre certain qu'il "gagne" (sinon
# l'inference bascule silencieusement sur CPU, ~10x plus lent, malgre un GPU
# disponible et detecte par nvidia-smi).
RUN pip install --no-cache-dir --force-reinstall --no-deps "onnxruntime-gpu>=1.19.0"

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python3 -m scripts.seed_admin && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

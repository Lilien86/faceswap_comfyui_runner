################################################################################
# Multi-stage build pour ComfyUI + dépendances CUDA 12.4
################################################################################

# Stage 1: Build dependencies
FROM nvidia/cuda:12.4.0-base-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Installer les outils de build nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev \
    build-essential \
    git wget ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Fix pour utiliser python3 comme commande par défaut
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Installer et compiler les dépendances Python
WORKDIR /root/build

# Cloner ComfyUI sans historique Git
RUN git clone --depth=1 https://github.com/comfyanonymous/ComfyUI.git /root/build/ComfyUI \
    && rm -rf /root/build/ComfyUI/.git

# Installer les dépendances Python dans un environnement virtuel
RUN pip install --upgrade pip wheel setuptools \
    && pip install --no-cache-dir -r /root/build/ComfyUI/requirements.txt \
    && pip install --no-cache-dir xformers==0.0.29.post3 torch==2.6.0 torchvision torchaudio \
        --index-url https://download.pytorch.org/whl/cu124 \
        --extra-index-url https://pypi.org/simple \
    && pip install --no-cache-dir piexif segment_anything runpod websockets websocket-client

# Stage 2: Runtime image
FROM nvidia/cuda:12.4.0-base-ubuntu22.04

LABEL maintainer="YAN Wenkun <code@yanwk.fun>"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV COMFYUI_NO_DOWNLOAD=1
ENV COMFYUI_SKIP_AUTODOWNLOAD=1

# Installer uniquement les dépendances runtime nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    python3-wheel python3-setuptools python3-aiohttp \
    python3-numpy python3-opencv \
    ffmpeg libgl1 libsm6 libxext6 \
    git wget ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Fix pour utiliser python3 comme commande par défaut
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Copier les fichiers compilés depuis le builder
WORKDIR /root
COPY --from=builder /usr/local/lib/python3 /usr/local/lib/python3
COPY --from=builder /root/build/ComfyUI /root/ComfyUI

# Bind libs pour Ubuntu
ENV LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/local/lib/python3/dist-packages/torch/lib:/usr/local/lib/python3/dist-packages/nvidia/cudnn/lib"

# Copier les fichiers du projet
COPY custom_nodes/. /root/ComfyUI/custom_nodes/
COPY handler.py /root/handler.py
COPY workflow_faceswap.json /root/workflow_faceswap.json
COPY testWF.json /root/testWF.json
COPY images/ /root/images/
COPY runpod.json /root/runpod.json

# Nettoyage final
RUN find /root -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Variables d'environnement
ENV CLI_ARGS=""

# Exposer le port web
EXPOSE 8188

# Commande de démarrage pour serverless RunPod
CMD ["python3", "/root/handler.py"]
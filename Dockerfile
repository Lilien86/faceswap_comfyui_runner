################################################################################
# newDockerfile: ComfyUI + dépendances CUDA 12.4 + custom_nodes intégrés (optimisé)
################################################################################

# Utiliser une image plus légère basée sur Debian
FROM nvidia/cuda:12.4.0-base-ubuntu22.04

LABEL maintainer="YAN Wenkun <code@yanwk.fun>"

# Éviter les interactions utilisateur et configurer l'environnement
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV COMFYUI_NO_DOWNLOAD=1
ENV COMFYUI_SKIP_AUTODOWNLOAD=1

RUN set -eu

################################################################################
# Python et outils système (version allégée)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev \
    python3-wheel python3-setuptools python3-aiohttp \
    python3-numpy python3-opencv \
    ffmpeg libgl1 libsm6 libxext6 \
    git wget ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Fix pour utiliser python3 comme commande par défaut
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Installer les packages de compilation nécessaires pour PyTorch
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

################################################################################
# PyTorch et xformers CUDA 12.4 (installation simplifiée)
RUN pip install --upgrade pip wheel setuptools \
    && pip install xformers==0.0.29.post3 torch==2.6.0 torchvision torchaudio \
        --index-url https://download.pytorch.org/whl/cu124 \
        --extra-index-url https://pypi.org/simple \
    && pip cache purge

# Bind libs (.so files) pour Ubuntu
ENV LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/local/lib/python3/dist-packages/torch/lib:/usr/local/lib/python3/dist-packages/nvidia/cudnn/lib"

################################################################################
# Installer ComfyUI (version optimisée)
WORKDIR /root

# Cloner ComfyUI sans historique Git
RUN git clone --depth=1 https://github.com/comfyanonymous/ComfyUI.git /root/ComfyUI \
    && rm -rf /root/ComfyUI/.git

# Installer les dépendances Python de ComfyUI en une seule étape
RUN pip install --no-cache-dir -r /root/ComfyUI/requirements.txt \
    && pip install --no-cache-dir piexif segment_anything runpod websockets websocket-client \
    && pip cache purge

################################################################################
COPY custom_nodes/. /root/ComfyUI/custom_nodes/

COPY handler.py /root/handler.py
COPY workflow_faceswap.json /root/workflow_faceswap.json
COPY testWF.json /root/testWF.json
COPY images/ /root/images/

################################################################################
# (Optionnel) Copier d'autres fichiers utiles
# COPY workflow_faceswap.json /root/workflow_faceswap.json

################################################################################
# Nettoyage final pour réduire la taille de l'image
RUN apt-get clean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    find /root -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Variables d'environnement
ENV CLI_ARGS=""

# Exposer le port web
EXPOSE 8188

# Commande de démarrage pour serverless RunPod
CMD ["python3", "/root/handler.py"]

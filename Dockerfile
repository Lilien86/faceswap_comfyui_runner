FROM runpod/base:0.6.3-cuda11.8.0

RUN ln -sf $(which python3.11) /usr/local/bin/python && \
    ln -sf $(which python3.11) /usr/local/bin/python3

COPY requirements.txt /requirements.txt
RUN uv pip install --upgrade -r /requirements.txt --no-cache-dir --system

RUN git clone --depth=1 https://github.com/comfyanonymous/ComfyUI.git /ComfyUI \
    && rm -rf /ComfyUI/.git

RUN pip install --no-cache-dir -r /ComfyUI/requirements.txt && pip cache purge

ADD workflow_faceswap.json /workflow_faceswap.json
ADD testWF.json /testWF.json

ADD handler.py .
ADD test_input.json .

ADD images/ /images/
ADD custom_nodes/. /ComfyUI/custom_nodes/

RUN find /ComfyUI -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

ENV PYTHONPATH="$PYTHONPATH:/ComfyUI"

EXPOSE 8188

CMD python -u /handler.py
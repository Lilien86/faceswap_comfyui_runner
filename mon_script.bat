@echo off
REM download_models.bat — téléchargements directs avec URLs

REM 1. Définir votre token Hugging Face
REM Vérifier si le token existe déjà dans l'environnement
if not defined HF_TOKEN (
    echo Veuillez saisir votre token Hugging Face:
    set /p HF_TOKEN=Token: 
)
REM Pour utiliser: définissez HF_TOKEN comme variable d'environnement ou saisissez-le quand demandé

REM 2. Installer Hugging Face CLI (silencieux)
pip install huggingface_hub --quiet

REM 3. Créer tous les dossiers cibles
mkdir models\diffusion_models 2>nul
mkdir models\vae 2>nul
mkdir models\loras 2>nul
mkdir models\upscale_models 2>nul
mkdir models\clip 2>nul
mkdir models\sams 2>nul
mkdir models\ultralytics\bbox 2>nul

REM 4. Télécharger chaque modèle avec curl (Windows 10+ intègre curl)

REM Diffusion model
curl -L -H "Authorization: Bearer %HF_TOKEN%" ^
  "https://huggingface.co/black-forest-labs/FLUX.1-Fill-dev/resolve/main/flux1-fill-dev.safetensors" ^
  -o models\diffusion_models\flux1-fill-dev.safetensors

REM VAE
curl -L -H "Authorization: Bearer %HF_TOKEN%" ^
  "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/vae/diffusion_pytorch_model.safetensors" ^
  -o models\vae\diffusion_pytorch_model.safetensors

REM LORA
curl -L -H "Authorization: Bearer %HF_TOKEN%" ^
  "https://huggingface.co/ali-vilab/ACE_Plus/resolve/main/portrait/comfyui_portrait_lora64.safetensors" ^
  -o models\loras\comfyui_portrait_lora64.safetensors

REM Upscale model
curl -L -H "Authorization: Bearer %HF_TOKEN%" ^
  "https://huggingface.co/ai-forever/Real-ESRGAN/resolve/main/RealESRGAN_x2.pth" ^
  -o models\upscale_models\RealESRGAN_x2.pth

REM SAM
curl -L -H "Authorization: Bearer %HF_TOKEN%" ^
  "https://huggingface.co/datasets/Gourieff/ReActor/resolve/main/models/sams/sam_vit_b_01ec64.pth" ^
  -o models\sams\sam_vit_b_01ec64.pth

REM Ultralytics bbox
curl -L -H "Authorization: Bearer %HF_TOKEN%" ^
  "https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8m.pt" ^
  -o models\ultralytics\bbox\face_yolov8m.pt

REM CLIP encoder
curl -L -H "Authorization: Bearer %HF_TOKEN%" ^
  "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors" ^
  -o models\clip\clip_l.safetensors

REM T5 encoder
curl -L -H "Authorization: Bearer %HF_TOKEN%" ^
  "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors" ^
  -o models\clip\t5xxl_fp16.safetensors

echo ✔ All downloads complete!
pause

import runpod
import json
import urllib.request
import urllib.parse
import uuid
import websocket
import base64
import subprocess
import time
import os
import signal

WORKFLOW_PATH = "workflow_faceswap.json"
# WORKFLOW_PATH = "testWF.json"
COMFYUI_HOST = "127.0.0.1:8188"  # À adapter si besoin
comfyui_process = None

def start_comfyui():
    global comfyui_process
    if comfyui_process is None:
        comfyui_process = subprocess.Popen(
            ["python3", "/root/ComfyUI/main.py", "--listen", "--port", "8188"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Attendre que ComfyUI soit prêt
        ready = False
        timeout = 60  # secondes
        start_time = time.time()
        while not ready and time.time() - start_time < timeout:
            try:
                with urllib.request.urlopen(f"http://{COMFYUI_HOST}/system_stats") as response:
                    if response.status == 200:
                        ready = True
                        break
            except:
                time.sleep(1)
        return ready
    return True

def setup_model_symlinks():
    """Crée des liens symboliques pour les modèles depuis le Network Storage"""
    network_storage_path = "/runpod-volume"  # Ajustez selon votre configuration
    comfyui_models_path = "/root/ComfyUI/models"
    
    # Créer le dossier models s'il n'existe pas
    if not os.path.exists(comfyui_models_path):
        os.makedirs(comfyui_models_path, exist_ok=True)
    
    # Vérifier si le dossier models existe dans le Network Storage
    network_models_path = os.path.join(network_storage_path, "models")
    if os.path.exists(network_models_path):
        # Lister les sous-dossiers de models (checkpoints, loras, etc.)
        model_subfolders = os.listdir(network_models_path)
        
        for subfolder in model_subfolders:
            source_path = os.path.join(network_models_path, subfolder)
            target_path = os.path.join(comfyui_models_path, subfolder)
            
            # Si le chemin cible existe et est un lien symbolique, le supprimer
            if os.path.islink(target_path):
                os.unlink(target_path)
            # Si c'est un dossier existant, le renommer
            elif os.path.isdir(target_path):
                os.rename(target_path, f"{target_path}_original")
            
            # Créer le lien symbolique
            os.symlink(source_path, target_path)
            print(f"Lien symbolique créé: {source_path} -> {target_path}")

def handler(event):
    # Démarrer ComfyUI si ce n'est pas déjà fait
    if not start_comfyui():
        return {"error": "Impossible de démarrer ComfyUI", "status": "error"}
    
    setup_model_symlinks()
    
    input_data = event["input"]
    image1_path = input_data["image1_path"]
    image2_path = input_data["image2_path"]

    # Charger et modifier le workflow
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        workflow = json.load(f)
    if "240" in workflow:
        workflow["240"]["inputs"]["image"] = image1_path
    if "431" in workflow:
        workflow["431"]["inputs"]["image"] = image2_path
    # if "1" in workflow:
    #     workflow["1"]["inputs"]["image"] = image1_path
    # if "2" in workflow:
    #     workflow["2"]["inputs"]["image"] = image2_path

    # 1. Générer un client_id unique
    client_id = str(uuid.uuid4())

    # 2. Envoyer le workflow à ComfyUI
    prompt = {"prompt": workflow, "client_id": client_id}
    data = json.dumps(prompt).encode('utf-8')
    req = urllib.request.Request(
        f"http://{COMFYUI_HOST}/prompt", data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        resp_json = json.loads(resp.read())
    prompt_id = resp_json['prompt_id']

    # 3. Attendre la fin de l’exécution via WebSocket
    ws = websocket.WebSocket()
    ws.connect(f"ws://{COMFYUI_HOST}/ws?clientId={client_id}")
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break  # Fin d'exécution
        else:
            continue
    ws.close()

    # 4. Récupérer l’historique et l’image du node 413
    with urllib.request.urlopen(f"http://{COMFYUI_HOST}/history/{prompt_id}") as response:
        history = json.loads(response.read())
    history = history[prompt_id]

    output_images = []
    node_id = "413"  # Node SaveImage
    # node_id = "11"  # Node SaveImage  
    node_output = history['outputs'].get(node_id, {})
    if 'images' in node_output:
        for image in node_output['images']:
            params = urllib.parse.urlencode({
                "filename": image['filename'],
                "subfolder": image['subfolder'],
                "type": image['type']
            })
            with urllib.request.urlopen(f"http://{COMFYUI_HOST}/view?{params}") as img_resp:
                img_bytes = img_resp.read()
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                output_images.append(img_b64)

    return {
        "status": "success",
        "prompt_id": prompt_id,
        "output_images": output_images,  # Liste d'images (base64)
        "message": f"{len(output_images)} image(s) générée(s) par le node 413."
    }

runpod.serverless.start({"handler": handler})

# if __name__ == "__main__":
#     # Remplace les chemins par ceux de tes images accessibles dans le conteneur ou sur ta machine
#     test_event = {"input": {
#         "image1_path": "/root/images/input.jpg",
#         "image2_path": "/root/images/target.jpg"
#     }}
#     result = handler(test_event)
#     print(json.dumps(result, indent=2, ensure_ascii=False))
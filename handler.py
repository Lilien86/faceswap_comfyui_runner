# TEST EARLY LOGGING
import sys
print("HANDLER STARTING - EARLY LOG", file=sys.stderr)
sys.stderr.flush()

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
import logging
import traceback
from typing import Dict, Any, List, Optional

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("comfyui-faceswap")

# Config
WORKFLOW_PATH = os.environ.get("WORKFLOW_PATH", "good.json")
COMFYUI_HOST = os.environ.get("COMFYUI_HOST", "127.0.0.1:8188")
NETWORK_STORAGE_PATH = os.environ.get("NETWORK_STORAGE_PATH", "/runpod-volume")
COMFYUI_TIMEOUT = int(os.environ.get("COMFYUI_TIMEOUT", "120"))  # Augmenté à 120 secondes
COMFYUI_PATH = os.environ.get("COMFYUI_PATH", "/ComfyUI")  # Chemin vers l'installation de ComfyUI

# Global variables
comfyui_process = None

def start_comfyui() -> bool:
    """Start ComfyUI if not already running"""
    global comfyui_process
    try:
        if comfyui_process is None:
            # Vérifier que le chemin vers ComfyUI existe
            comfyui_main_path = os.path.join(COMFYUI_PATH, "main.py")
            if not os.path.exists(comfyui_main_path):
                print(f"ERROR: ComfyUI main.py not found at {comfyui_main_path}", file=sys.stderr)
                # Essayer de trouver main.py ailleurs
                potential_paths = ["/root/ComfyUI/main.py", "/ComfyUI/main.py", "./ComfyUI/main.py"]
                for path in potential_paths:
                    if os.path.exists(path):
                        comfyui_main_path = path
                        print(f"Found ComfyUI main.py at {comfyui_main_path}", file=sys.stderr)
                        break
                else:
                    print("CRITICAL ERROR: Could not find ComfyUI main.py anywhere!", file=sys.stderr)
                    print(f"Current directory contents: {os.listdir('.')}", file=sys.stderr)
                    print(f"Root directory contents: {os.listdir('/')}", file=sys.stderr)
                    sys.stderr.flush()
                    return False
            
            print(f"Starting ComfyUI from {comfyui_main_path}...", file=sys.stderr)
            sys.stderr.flush()
            
            # Lancer ComfyUI avec uniquement les options reconnues
            comfyui_process = subprocess.Popen(
                [
                    "python", comfyui_main_path,
                    "--listen", "--port", "8188",
                    "--cpu"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "COMFYUI_NO_DOWNLOAD": "1", "COMFYUI_SKIP_AUTODOWNLOAD": "1"}
            )
            
            ready = False
            start_time = time.time()
            while not ready and time.time() - start_time < COMFYUI_TIMEOUT:
                try:
                    with urllib.request.urlopen(f"http://{COMFYUI_HOST}/system_stats") as response:
                        if response.status == 200:
                            print("ComfyUI started and ready!", file=sys.stderr)
                            sys.stderr.flush()
                            ready = True
                            break
                except Exception as e:
                    # Vérifier si le processus est toujours en cours
                    if comfyui_process.poll() is not None:
                        # Le processus s'est arrêté, récupérer la sortie
                        stdout, stderr = comfyui_process.communicate()
                        print(f"\n[ERROR] ComfyUI process terminated with code {comfyui_process.returncode}", file=sys.stderr)
                        print(f"\n[ComfyUI STDOUT]:\n{stdout.decode()}", file=sys.stderr)
                        print(f"\n[ComfyUI STDERR]:\n{stderr.decode()}", file=sys.stderr)
                        sys.stderr.flush()
                        return False
                    
                    # Afficher un point pour montrer que ça travaille
                    if int(time.time() - start_time) % 5 == 0:
                        print(".", end="", file=sys.stderr)
                        sys.stderr.flush()
                    
                    time.sleep(1)
            
            if not ready:
                # Timeout atteint, afficher les logs ComfyUI pour diagnostic
                if comfyui_process is not None:
                    try:
                        comfyui_process.terminate()  # Terminer proprement
                        stdout, stderr = comfyui_process.communicate(timeout=5)
                        print(f"\n[ComfyUI STDOUT]:\n{stdout.decode()}", file=sys.stderr)
                        print(f"\n[ComfyUI STDERR]:\n{stderr.decode()}", file=sys.stderr)
                        sys.stderr.flush()
                    except Exception as e:
                        print(f"Error getting ComfyUI output: {str(e)}", file=sys.stderr)
                        sys.stderr.flush()
                
                print(f"Timeout starting ComfyUI after {COMFYUI_TIMEOUT} seconds", file=sys.stderr)
                sys.stderr.flush()
                return False
            
            return ready
        return True
    except Exception as e:
        print(f"Error starting ComfyUI: {str(e)}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        sys.stderr.flush()
        return False

# def setup_model_symlinks() -> bool:
#     """Create symlinks for models from Network Storage"""
#     try:
#         print(f"\n=== Setting up model symlinks ===\n", file=sys.stderr)
#         print(f"Network storage path: {NETWORK_STORAGE_PATH}", file=sys.stderr)
#         sys.stderr.flush()
        
#         # Utiliser le nouveau chemin vers ComfyUI
#         comfyui_models_path = os.path.join(COMFYUI_PATH, "models")
        
#         print(f"ComfyUI models path: {comfyui_models_path}", file=sys.stderr)
#         sys.stderr.flush()
        
#         # S'assurer que le dossier models existe
#         if not os.path.exists(comfyui_models_path):
#             try:
#                 os.makedirs(comfyui_models_path, exist_ok=True)
#                 print(f"Created ComfyUI models directory: {comfyui_models_path}", file=sys.stderr)
#             except Exception as e:
#                 print(f"Error creating models directory: {str(e)}", file=sys.stderr)
#                 print(traceback.format_exc(), file=sys.stderr)
#                 sys.stderr.flush()
#                 return False
        
#         # Vérifier si le chemin source existe
#         network_models_path = os.path.join(NETWORK_STORAGE_PATH, "models")
#         if not os.path.exists(network_models_path):
#             print(f"WARNING: Network models path {network_models_path} doesn't exist.", file=sys.stderr)
#             print(f"Available paths in {NETWORK_STORAGE_PATH}: {os.listdir(NETWORK_STORAGE_PATH) if os.path.exists(NETWORK_STORAGE_PATH) else 'NETWORK_STORAGE_PATH does not exist'}", file=sys.stderr)
#             print(f"Creating empty models directory structure for ComfyUI...", file=sys.stderr)
#             sys.stderr.flush()
            
#             # Créer les sous-dossiers models standard pour ComfyUI même sans données
#             model_folders = ["checkpoints", "embeddings", "loras", "upscale_models", "vae"]
#             for folder in model_folders:
#                 folder_path = os.path.join(comfyui_models_path, folder)
#                 if not os.path.exists(folder_path):
#                     try:
#                         os.makedirs(folder_path, exist_ok=True)
#                         print(f"Created empty folder: {folder_path}", file=sys.stderr)
#                     except Exception as e:
#                         print(f"Error creating {folder}: {str(e)}", file=sys.stderr)
            
#             print("Models structure created, but no models available.", file=sys.stderr)
#             sys.stderr.flush()
#             return True  # Retourne True car nous avons créé une structure minimale
        
#         # Liste des sous-dossiers dans network_models_path
#         try:
#             model_subfolders = os.listdir(network_models_path)
#             print(f"Found model subfolders: {model_subfolders}", file=sys.stderr)
#         except Exception as e:
#             print(f"Error listing network models: {str(e)}", file=sys.stderr)
#             print(traceback.format_exc(), file=sys.stderr)
#             sys.stderr.flush()
#             return False
        
#         # Créer les symlinks
#         symlinks_created = 0
#         for subfolder in model_subfolders:
#             source_path = os.path.join(network_models_path, subfolder)
#             target_path = os.path.join(comfyui_models_path, subfolder)
            
#             try:
#                 # Gérer les symlinks existants
#                 if os.path.islink(target_path):
#                     print(f"Removing existing symlink: {target_path}", file=sys.stderr)
#                     os.unlink(target_path)
#                 # Gérer les dossiers existants
#                 elif os.path.isdir(target_path):
#                     print(f"Renaming existing directory: {target_path} -> {target_path}_original", file=sys.stderr)
#                     os.rename(target_path, f"{target_path}_original")
                
#                 # Créer le symlink
#                 os.symlink(source_path, target_path)
#                 symlinks_created += 1
#                 print(f"Symlink created: {source_path} -> {target_path}", file=sys.stderr)
#             except Exception as e:
#                 print(f"Error creating symlink for {subfolder}: {str(e)}", file=sys.stderr)
#                 print(traceback.format_exc(), file=sys.stderr)
#                 # Continuer avec les autres dossiers même si celui-ci échoue
        
#         print(f"=== Model symlinks setup completed: {symlinks_created} symlinks created ===\n", file=sys.stderr)
#         sys.stderr.flush()
#         return True
#     except Exception as e:
#         print(f"CRITICAL ERROR in setup_model_symlinks: {str(e)}", file=sys.stderr)
#         print(traceback.format_exc(), file=sys.stderr)
#         sys.stderr.flush()
#         return False

def validate_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input data with detailed error messages"""
    errors = []
    
    # Log actual input for debugging
    logger.info(f"Validating input: {json.dumps(input_data, indent=2)}")
    
    # Check if image1_path exists in input
    if "image1_path" not in input_data:
        errors.append("Image 1 path ('image1_path') is required")
    else:
        # Check if the path exists
        image1_path = input_data["image1_path"]
        logger.info(f"Checking if image1 exists at: {image1_path}")
        if not os.path.exists(image1_path):
            errors.append(f"Image 1 doesn't exist at path: {image1_path}")
            # List available files in /root/images for debugging
            try:
                if os.path.exists("/root/images"):
                    available_files = os.listdir("/root/images")
                    logger.info(f"Available files in /root/images: {available_files}")
            except Exception as e:
                logger.error(f"Error listing /root/images: {str(e)}")
    
    # Check if image2_path exists in input
    if "image2_path" not in input_data:
        errors.append("Image 2 path ('image2_path') is required")
    else:
        # Check if the path exists
        image2_path = input_data["image2_path"]
        logger.info(f"Checking if image2 exists at: {image2_path}")
        if not os.path.exists(image2_path):
            errors.append(f"Image 2 doesn't exist at path: {image2_path}")
    
    if errors:
        return {"valid": False, "errors": errors}
    
    return {"valid": True, "data": input_data}

def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    try:
        comfyui_running = comfyui_process is not None and comfyui_process.poll() is None
        
        comfyui_api_accessible = False
        try:
            with urllib.request.urlopen(f"http://{COMFYUI_HOST}/system_stats") as response:
                if response.status == 200:
                    comfyui_api_accessible = True
        except:
            pass
        
        workflow_exists = os.path.exists(WORKFLOW_PATH)
        network_storage_accessible = os.path.exists(NETWORK_STORAGE_PATH)
        
        is_healthy = comfyui_running and comfyui_api_accessible and workflow_exists
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "details": {
                "comfyui_running": comfyui_running,
                "comfyui_api_accessible": comfyui_api_accessible,
                "workflow_exists": workflow_exists,
                "network_storage_accessible": network_storage_accessible
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def handler(job):
    """Main handler for RunPod Serverless jobs (faceswap via ComfyUI)."""
    print(f"Handler called with job: {job}", file=sys.stderr)
    sys.stderr.flush()

    try:
        # Health check
        if job.get("health_check", False):
            return health_check()

        # Input validation
        job_input = job.get("input", {})
        input_validation = validate_input(job_input)
        if not input_validation["valid"]:
            return {
                "status": "error",
                "error": input_validation["errors"],
                "details": "Input validation failed"
            }
        input_data = input_validation["data"]

        # Start ComfyUI
        if not start_comfyui():
            return {
                "status": "error",
                "error": "Failed to start ComfyUI",
                "details": "ComfyUI server failed to start or respond within the timeout period"
            }

        # Charger le workflow
        try:
            with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
                workflow = json.load(f)
        except Exception as e:
            return {"status": "error", "error": f"Error loading workflow: {str(e)}"}

        # Convertir les chemins relatifs en chemins absolus
        image1_path = input_data["image1_path"]
        image2_path = input_data["image2_path"]
        
        # Vérifier si les chemins sont absolus, sinon les convertir
        if not os.path.isabs(image1_path):
            image1_path = os.path.abspath(image1_path)
        if not os.path.isabs(image2_path):
            image2_path = os.path.abspath(image2_path)

        print(f"Processing faceswap with image1: {image1_path}, image2: {image2_path}", file=sys.stderr)
        sys.stderr.flush()

        # Vérifier les nodes dans le workflow
        print(f"Workflow contains these nodes: {list(workflow.keys())}", file=sys.stderr)
        sys.stderr.flush()
        
        # Update workflow with image paths
        # Détection des nodes d'entrée d'image - chercher des noms de clef génériques
        image_nodes_updated = False
        
        # Chercher les nodes LoadImage dans le workflow
        for node_id, node in workflow.items():
            if node.get("class_type") == "LoadImage":
                print(f"Found LoadImage node {node_id}: {node}", file=sys.stderr)
                if not image_nodes_updated:
                    # Premier node = image1, second = image2
                    print(f"Setting node {node_id} to use image1: {image1_path}", file=sys.stderr)
                    node["inputs"]["image"] = image1_path
                    image_nodes_updated = True
                else:
                    print(f"Setting node {node_id} to use image2: {image2_path}", file=sys.stderr)
                    node["inputs"]["image"] = image2_path
                    break

        # Fallback - utiliser les IDs spécifiés si les LoadImage n'ont pas été trouvés
        if not image_nodes_updated:
            if "240" in workflow:
                print(f"Using fallback node 240 for image1", file=sys.stderr)
                workflow["240"]["inputs"]["image"] = image1_path
            if "431" in workflow:
                print(f"Using fallback node 431 for image2", file=sys.stderr)
                workflow["431"]["inputs"]["image"] = image2_path
        
        sys.stderr.flush()

        # Generate unique client_id
        client_id = str(uuid.uuid4())

        # Send workflow to ComfyUI
        prompt = {"prompt": workflow, "client_id": client_id}
        data = json.dumps(prompt).encode('utf-8')
        
        # Debug: afficher le prompt envoyé (format condensé pour éviter trop de logs)
        debug_prompt = json.dumps(prompt, indent=None)
        print(f"Sending prompt to ComfyUI: {debug_prompt[:200]}... (truncated)", file=sys.stderr)
        sys.stderr.flush()

        try:
            req = urllib.request.Request(
                f"http://{COMFYUI_HOST}/prompt", data=data,
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req) as resp:
                    resp_content = resp.read()
                    resp_json = json.loads(resp_content)
                prompt_id = resp_json['prompt_id']
                print(f"Prompt sent successfully, ID: {prompt_id}", file=sys.stderr)
                sys.stderr.flush()
            except urllib.error.HTTPError as http_err:
                # Capturer plus de détails sur l'erreur HTTP
                error_body = http_err.read().decode('utf-8')
                print(f"HTTP Error {http_err.code}: {http_err.reason}", file=sys.stderr)
                print(f"Error details: {error_body}", file=sys.stderr)
                sys.stderr.flush()
                return {"status": "error", "error": f"HTTP Error {http_err.code}: {http_err.reason}", "details": error_body}
        except Exception as e:
            print(f"Exception sending prompt: {str(e)}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            sys.stderr.flush()
            return {"status": "error", "error": f"Error sending prompt to ComfyUI: {str(e)}"}

        # Wait for execution via WebSocket
        try:
            ws = websocket.WebSocket()
            ws.connect(f"ws://{COMFYUI_HOST}/ws?clientId={client_id}")
            ws.settimeout(300)  # 5 minutes max
            execution_start = time.time()
            while True:
                try:
                    out = ws.recv()
                    if isinstance(out, str):
                        message = json.loads(out)
                        if message['type'] == 'executing':
                            data = message['data']
                            if data['node'] is None and data['prompt_id'] == prompt_id:
                                print(f"Execution completed in {time.time() - execution_start:.2f} seconds", file=sys.stderr)
                                sys.stderr.flush()
                                break  # Execution completed
                    if time.time() - execution_start > 300:
                        return {"status": "error", "error": "Timeout during workflow execution"}
                except websocket.WebSocketTimeoutException:
                    return {"status": "error", "error": "Timeout waiting for WebSocket results"}
            ws.close()
        except Exception as e:
            return {"status": "error", "error": f"WebSocket communication error: {str(e)}"}

        # Get history and image from node 413
        try:
            with urllib.request.urlopen(f"http://{COMFYUI_HOST}/history/{prompt_id}") as response:
                history = json.loads(response.read())
            history = history[prompt_id]
        except Exception as e:
            return {"status": "error", "error": f"Error retrieving history: {str(e)}"}

        # Get generated images
        output_images = []
        node_id = "413"  # SaveImage node
        try:
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
                print(f"{len(output_images)} image(s) retrieved from node {node_id}", file=sys.stderr)
                sys.stderr.flush()
        except Exception as e:
            return {"status": "error", "error": f"Error retrieving images: {str(e)}"}

        return {
            "status": "success",
            "prompt_id": prompt_id,
            "output_images": output_images,
            "message": f"{len(output_images)} image(s) generated by node {node_id}."
        }

    except Exception as e:
        print(f"Unhandled error: {str(e)}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        sys.stderr.flush()
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

# Entry point for runpod.serverless - format conforme à la documentation RunPod
runpod.serverless.start({"handler": handler})

if __name__ == "__main__":
    # Test local : charger test_input.json, appeler handler, afficher la sortie
    import sys
    import json
    try:
        with open("test_input.json", "r", encoding="utf-8") as f:
            test_job = json.load(f)
        print("\n=== [LOCAL TEST] test_input.json loaded ===\n", file=sys.stderr)
        sys.stderr.flush()
        result = handler(test_job)
        print("\n=== [LOCAL TEST] Handler output ===\n", file=sys.stderr)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.stderr.flush()
    except Exception as e:
        print(f"[LOCAL TEST ERROR] {e}", file=sys.stderr)
        import traceback
        print(traceback.format_exc(), file=sys.stderr)
        sys.stderr.flush()
    sys.stderr.flush()
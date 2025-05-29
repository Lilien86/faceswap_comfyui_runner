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
import sys
from typing import Dict, Any, List, Optional

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("comfyui-faceswap")

# Config
WORKFLOW_PATH = os.environ.get("WORKFLOW_PATH", "workflow_faceswap.json")
COMFYUI_HOST = os.environ.get("COMFYUI_HOST", "127.0.0.1:8188")
NETWORK_STORAGE_PATH = os.environ.get("NETWORK_STORAGE_PATH", "/runpod-volume")
COMFYUI_TIMEOUT = int(os.environ.get("COMFYUI_TIMEOUT", "60"))

# Global variables
comfyui_process = None

def start_comfyui() -> bool:
    """Start ComfyUI if not already running"""
    global comfyui_process
    try:
        if comfyui_process is None:
            logger.info("Starting ComfyUI...")
            comfyui_process = subprocess.Popen(
                ["python3", "/root/ComfyUI/main.py", "--listen", "--port", "8188"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            ready = False
            start_time = time.time()
            while not ready and time.time() - start_time < COMFYUI_TIMEOUT:
                try:
                    with urllib.request.urlopen(f"http://{COMFYUI_HOST}/system_stats") as response:
                        if response.status == 200:
                            logger.info("ComfyUI started and ready")
                            ready = True
                            break
                except Exception as e:
                    time.sleep(1)
            
            if not ready:
                logger.error(f"Timeout starting ComfyUI after {COMFYUI_TIMEOUT} seconds")
                return False
            return ready
        return True
    except Exception as e:
        logger.error(f"Error starting ComfyUI: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def setup_model_symlinks() -> bool:
    """Create symlinks for models from Network Storage"""
    try:
        logger.info(f"Setting up symlinks from {NETWORK_STORAGE_PATH}")
        comfyui_models_path = "/root/ComfyUI/models"
        
        if not os.path.exists(comfyui_models_path):
            os.makedirs(comfyui_models_path, exist_ok=True)
        
        network_models_path = os.path.join(NETWORK_STORAGE_PATH, "models")
        if not os.path.exists(network_models_path):
            logger.warning(f"Path {network_models_path} doesn't exist. No symlinks created.")
            return False
            
        model_subfolders = os.listdir(network_models_path)
        
        for subfolder in model_subfolders:
            source_path = os.path.join(network_models_path, subfolder)
            target_path = os.path.join(comfyui_models_path, subfolder)
            
            if os.path.islink(target_path):
                os.unlink(target_path)
            elif os.path.isdir(target_path):
                os.rename(target_path, f"{target_path}_original")
            
            os.symlink(source_path, target_path)
            logger.info(f"Symlink created: {source_path} -> {target_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error setting up symlinks: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def validate_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input data"""
    errors = []
    
    if "image1_path" not in input_data:
        errors.append("Image 1 path is required")
    elif not os.path.exists(input_data["image1_path"]):
        errors.append(f"Image 1 doesn't exist: {input_data['image1_path']}")
        
    if "image2_path" not in input_data:
        errors.append("Image 2 path is required")
    elif not os.path.exists(input_data["image2_path"]):
        errors.append(f"Image 2 doesn't exist: {input_data['image2_path']}")
    
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

def handler(event):
    """Main handler for RunPod requests"""
    try:
        if event.get("health_check", False):
            return health_check()
        
        if "input" not in event:
            return {"error": "No input data provided", "status": "error"}
        
        input_validation = validate_input(event["input"])
        if not input_validation["valid"]:
            return {"error": input_validation["errors"], "status": "error"}
        
        input_data = input_validation["data"]
        
        if not start_comfyui():
            return {"error": "Failed to start ComfyUI", "status": "error"}
        
        setup_model_symlinks()
        
        try:
            with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
                workflow = json.load(f)
        except Exception as e:
            return {"error": f"Error loading workflow: {str(e)}", "status": "error"}
        
        image1_path = input_data["image1_path"]
        image2_path = input_data["image2_path"]
        
        logger.info(f"Processing faceswap with image1: {image1_path}, image2: {image2_path}")
        
        # Update workflow with image paths
        if "240" in workflow:
            workflow["240"]["inputs"]["image"] = image1_path
        if "431" in workflow:
            workflow["431"]["inputs"]["image"] = image2_path
        
        # Generate unique client_id
        client_id = str(uuid.uuid4())
        
        # Send workflow to ComfyUI
        prompt = {"prompt": workflow, "client_id": client_id}
        data = json.dumps(prompt).encode('utf-8')
        
        try:
            req = urllib.request.Request(
                f"http://{COMFYUI_HOST}/prompt", data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req) as resp:
                resp_json = json.loads(resp.read())
            
            prompt_id = resp_json['prompt_id']
            logger.info(f"Prompt sent successfully, ID: {prompt_id}")
        except Exception as e:
            return {"error": f"Error sending prompt to ComfyUI: {str(e)}", "status": "error"}
        
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
                                logger.info(f"Execution completed in {time.time() - execution_start:.2f} seconds")
                                break  # Execution completed
                    
                    if time.time() - execution_start > 300:
                        return {"error": "Timeout during workflow execution", "status": "error"}
                        
                except websocket.WebSocketTimeoutException:
                    return {"error": "Timeout waiting for WebSocket results", "status": "error"}
            
            ws.close()
        except Exception as e:
            return {"error": f"WebSocket communication error: {str(e)}", "status": "error"}
        
        # Get history and image from node 413
        try:
            with urllib.request.urlopen(f"http://{COMFYUI_HOST}/history/{prompt_id}") as response:
                history = json.loads(response.read())
            history = history[prompt_id]
        except Exception as e:
            return {"error": f"Error retrieving history: {str(e)}", "status": "error"}
        
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
                        
                logger.info(f"{len(output_images)} image(s) retrieved from node {node_id}")
        except Exception as e:
            return {"error": f"Error retrieving images: {str(e)}", "status": "error"}
        
        return {
            "status": "success",
            "prompt_id": prompt_id,
            "output_images": output_images,
            "message": f"{len(output_images)} image(s) generated by node {node_id}."
        }
        
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

# Entry point for runpod.serverless
runpod.serverless.start({
    "handler": handler,
    "startupTimeout": COMFYUI_TIMEOUT + 30
})
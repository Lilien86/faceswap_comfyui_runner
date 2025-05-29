---
trigger: manual
---

{
  "project_name": "FaceSwap ComfyUI Runner",
  "version": "1.0.0",
  "description": "A containerized application that automates face swapping using ComfyUI workflows",
  "purpose": "This project provides a streamlined solution for face swapping between two images, using the powerful ComfyUI backend and custom workflows. It's designed to be deployed as a standalone service or as a serverless function on RunPod.",
  "technologies": {
    "main_framework": "ComfyUI",
    "programming_languages": ["Python 3"],
    "containerization": ["Docker", "Docker Compose"],
    "gpu_acceleration": "NVIDIA CUDA 12.4",
    "serverless": "RunPod API"
  },
  "system_requirements": {
    "operating_system": "Windows",
    "hardware": "NVIDIA GPU with CUDA support",
    "docker": "Docker Desktop for Windows"
  },
  "key_components": {
    "workflows": {
      "workflow_faceswap.json": "Main face swapping workflow configuration",
      "testWF.json": "Test workflow for development purposes"
    },
    "scripts": {
      "handler.py": "Main Python script that orchestrates the face swapping process",
      "mon_script_clean.bat": "Batch script for local execution (without hardcoded credentials)"
    },
    "docker": {
      "Dockerfile": "Custom Docker image definition with ComfyUI and dependencies",
      "docker-compose.yml": "Container orchestration configuration"
    },
    "folders": {
      "custom_nodes": "Custom ComfyUI nodes for enhanced functionality",
      "models": "Storage for AI models (mounted as volume)",
      "images": "Example images for testing the face swap functionality"
    }
  },
  "execution_flow": {
    "1": "Images are provided through the API input",
    "2": "The handler.py script starts ComfyUI server if not running",
    "3": "The workflow is loaded and configured with the input images",
    "4": "ComfyUI processes the images using the configured workflow",
    "5": "The resulting face-swapped image is returned as base64 encoded data"
  },
  "deployment_options": {
    "local": "Run locally using Docker Compose",
    "cloud": "Deploy as a serverless endpoint on RunPod"
  },
  "security_notes": "API tokens and credentials should be provided through environment variables rather than being hardcoded in scripts"
}

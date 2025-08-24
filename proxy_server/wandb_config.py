"""
Weights & Biases Configuration for Automatic Setup
"""

import os
import wandb
from pathlib import Path

def setup_wandb():
    """Setup wandb with automatic configuration"""
    
    # Set environment variables for automatic wandb setup
    os.environ["WANDB_API_KEY"] = "2ac90cd4163f5b61805b142b04396e7190a47972"
    os.environ["WANDB_MODE"] = "online"
    os.environ["WANDB_SILENT"] = "true"
    
    # Create wandb directory if it doesn't exist
    wandb_dir = Path.home() / ".wandb"
    wandb_dir.mkdir(exist_ok=True)
    
    # Create settings file for automatic login
    settings_file = wandb_dir / "settings"
    if not settings_file.exists():
        settings_content = f"""[default]
project = bittensor-inference-subnet
entity = 
base_url = https://api.wandb.ai
api_key = 2ac90cd4163f5b61805b142b04396e7190a47972
"""
        settings_file.write_text(settings_content)
    
    print("✅ Wandb configuration set up automatically")
    print(f"🔑 API key configured: {os.environ['WANDB_API_KEY'][:8]}...")
    print(f"📁 Config directory: {wandb_dir}")

def get_wandb_config():
    """Get wandb configuration for the project"""
    return {
        "project": "bittensor-inference-subnet",
        "entity": None,  # Will use default entity
        "tags": ["subnet", "inference", "bittensor"],
        "notes": "Bittensor Inference Subnet - Proxy Server Monitoring",
        "config": {
            "subnet_name": "inference-subnet",
            "architecture": "proxy-validator-miner",
            "monitoring": True,
            "api_key_set": True,
            "version": "1.0.0"
        }
    }

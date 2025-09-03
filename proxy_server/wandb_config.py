#!/usr/bin/env python3
"""
Weights & Biases configuration for the Bittensor Audio Processing Proxy Server
"""

import os
import wandb
from typing import Dict, Any

def setup_wandb():
    """Setup wandb configuration"""
    try:
        # Use the provided API key
        api_key = "2ac90cd4163f5b61805b142b04396e7190a47972"
        wandb.login(key=api_key)
        print("✅ Wandb API key configured")
        return True
    except Exception as e:
        print(f"⚠️  Wandb login failed: {e}")
        os.environ["WANDB_MODE"] = "disabled"
        return False

def get_wandb_config() -> Dict[str, Any]:
    """Get wandb configuration"""
    return {
        "project": os.getenv("WANDB_PROJECT", "audio-processing-proxy"),
        "entity": os.getenv("WANDB_ENTITY", None),
        "tags": ["proxy-server", "audio-processing"],
        "notes": "Enhanced Audio Processing Proxy Server",
        "config": {
            "environment": os.getenv("ENVIRONMENT", "development"),
            "redis_host": os.getenv("REDIS_HOST", "localhost"),
            "redis_port": os.getenv("REDIS_PORT", "6379"),
            "max_concurrent_tasks": os.getenv("MAX_CONCURRENT_TASKS", "20"),
            "task_timeout": os.getenv("TASK_TIMEOUT", "120")
        }
    }

def init_wandb_run(project_name: str = "bittensor-subnet", entity: str = None):
    """Initialize a new wandb run"""
    try:
        # Setup wandb
        setup_wandb()
        
        # Get configuration
        config = get_wandb_config()
        
        # Initialize wandb run
        run = wandb.init(
            project=project_name or config["project"],
            entity=entity or config["entity"],
            tags=config["tags"],
            notes=config["notes"],
            config=config["config"],
            mode="online"
        )
        
        print(f"✅ Wandb run initialized: {run.url}")
        return run
        
    except Exception as e:
        print(f"⚠️  Failed to initialize wandb run: {e}")
        return None

def log_metrics(metrics: Dict[str, Any]):
    """Log metrics to wandb"""
    try:
        wandb.log(metrics)
    except Exception as e:
        print(f"⚠️  Failed to log metrics to wandb: {e}")

def finish_run():
    """Finish the current wandb run"""
    try:
        wandb.finish()
        print("✅ Wandb run finished")
    except Exception as e:
        print(f"⚠️  Failed to finish wandb run: {e}")
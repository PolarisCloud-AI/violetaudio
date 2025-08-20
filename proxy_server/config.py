#!/usr/bin/env python3
"""
Configuration file for the Bittensor Audio Processing Proxy Server
"""

import os
from typing import Optional

class Config:
    """Configuration class for the proxy server"""
    
    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # Bittensor settings
    BT_NETUID: int = int(os.getenv("BT_NETUID", "49"))
    BT_NETWORK: str = os.getenv("BT_NETWORK", "finney")
    BT_WALLET_NAME: str = os.getenv("BT_WALLET_NAME", "luno")
    BT_WALLET_HOTKEY: str = os.getenv("BT_WALLET_HOTKEY", "arusha")
    
    # Task processing settings
    MAX_CONCURRENT_TASKS: int = int(os.getenv("MAX_CONCURRENT_TASKS", "10"))
    TASK_TIMEOUT: int = int(os.getenv("TASK_TIMEOUT", "60"))
    MAX_MINERS_PER_REQUEST: int = int(os.getenv("MAX_MINERS_PER_REQUEST", "5"))
    
    # Scoring weights
    ACCURACY_WEIGHT: float = float(os.getenv("ACCURACY_WEIGHT", "0.7"))
    SPEED_WEIGHT: float = float(os.getenv("SPEED_WEIGHT", "0.3"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # CORS
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
    
    # Webhook settings
    WEBHOOK_TIMEOUT: int = int(os.getenv("WEBHOOK_TIMEOUT", "10"))
    MAX_WEBHOOK_RETRIES: int = int(os.getenv("MAX_WEBHOOK_RETRIES", "3"))

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = "WARNING"

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    REDIS_DB = 1

# Configuration mapping
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig
}

def get_config() -> Config:
    """Get configuration based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    return config_map.get(env, DevelopmentConfig)()

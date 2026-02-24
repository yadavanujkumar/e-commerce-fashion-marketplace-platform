import os
from typing import Any, Dict

class Config:
    """Base configuration class with common settings."""
    DEBUG: bool = False
    TESTING: bool = False
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'default_secret_key')
    DATABASE_URI: str = os.getenv('DATABASE_URI', 'sqlite:///default.db')
    CACHE_TYPE: str = os.getenv('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT: int = 300
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    TIMEZONE: str = os.getenv('TIMEZONE', 'UTC')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG: bool = True
    DATABASE_URI: str = os.getenv('DEV_DATABASE_URI', 'sqlite:///dev.db')
    CACHE_TYPE: str = 'null'
    LOG_LEVEL: str = 'DEBUG'

class StagingConfig(Config):
    """Staging configuration."""
    DEBUG: bool = False
    DATABASE_URI: str = os.getenv('STAGING_DATABASE_URI', 'postgresql://user:password@staging-db:5432/staging_db')
    CACHE_TYPE: str = 'redis'
    CACHE_REDIS_URL: str = os.getenv('CACHE_REDIS_URL', 'redis://localhost:6379/0')
    LOG_LEVEL: str = 'WARNING'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG: bool = False
    DATABASE_URI: str = os.getenv('PROD_DATABASE_URI', 'postgresql://user:password@prod-db:5432/prod_db')
    CACHE_TYPE: str = 'redis'
    CACHE_REDIS_URL: str = os.getenv('CACHE_REDIS_URL', 'redis://localhost:6379/0')
    LOG_LEVEL: str = 'ERROR'
    RESOURCE_LIMITS: Dict[str, Any] = {
        'max_connections': 100,
        'timeout': 30,
    }

def get_config(env: str) -> Config:
    """Factory function to get the appropriate configuration based on the environment."""
    if env == 'production':
        return ProductionConfig()
    elif env == 'staging':
        return StagingConfig()
    else:
        return DevelopmentConfig()

# Example usage:
# config = get_config(os.getenv('FLASK_ENV', 'development'))
import os
from typing import Optional
from pydantic_settings import BaseSettings

# Check if Azure SDK is available
try:
    import azure.storage.blob
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False


class AzureStorageSettings(BaseSettings):
    azure_storage_connection_string: str = os.getenv(
<<<<<<< HEAD
        "AZURE_STORAGE_CONNECTION_STRING",
=======
        "AZURE_STORAGE_CONNECTION_STRING",
>>>>>>> d148441 (feat: Q&A feedback bot .env)
    )
    
    # Container name for feedback photos
    azure_container_name: str = os.getenv("AZURE_CONTAINER_NAME", "feedback-photos")
    
    # Enable/disable Azure storage (fallback to local storage)
    # Automatically disabled if Azure SDK is not available
    azure_storage_enabled: bool = (
        AZURE_SDK_AVAILABLE and 
        os.getenv("AZURE_STORAGE_ENABLED", "true").lower() == "true"
    )
    
    # Local fallback directory
    local_storage_path: str = os.getenv("LOCAL_STORAGE_PATH", "temp_feedback_images")
    
    # Azure SDK availability flag
    azure_sdk_available: bool = AZURE_SDK_AVAILABLE

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from .env


# Global settings instance
azure_settings = AzureStorageSettings() 

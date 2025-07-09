import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
import aiofiles
import logging

# Optional Azure imports with fallback
try:
    from azure.storage.blob import BlobServiceClient, ContentSettings
    from azure.core.exceptions import AzureError
    AZURE_AVAILABLE = True
except ImportError:
    # Azure SDK not available, use fallback
    BlobServiceClient = None
    ContentSettings = None
    AzureError = Exception
    AZURE_AVAILABLE = False

from src.utils.azure_config import azure_settings

logger = logging.getLogger(__name__)


class AzureStorageManager:
    """Manager for Azure Blob Storage operations with fallback to local storage."""
    
    def __init__(self):
        self.settings = azure_settings
        self.blob_service_client = None
        
        # Check if Azure is available and enabled
        if AZURE_AVAILABLE and self.settings.azure_storage_enabled:
            try:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    self.settings.azure_storage_connection_string
                )
                logger.info("Azure Blob Storage client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Azure client: {e}")
                self.blob_service_client = None
        else:
            if not AZURE_AVAILABLE:
                logger.warning("Azure Storage SDK not available, falling back to local storage")
            else:
                logger.info("Azure Storage disabled, using local storage")
        
        # Ensure local directory exists as fallback
        self.local_dir = Path(self.settings.local_storage_path)
        self.local_dir.mkdir(exist_ok=True)
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension."""
        ext = Path(filename).suffix.lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp'
        }
        return content_types.get(ext, 'application/octet-stream')
    
    def _generate_blob_name(self, bot_id: int, feedback_id: int, original_filename: str) -> str:
        """Generate unique blob name for the file."""
        # Create unique filename to avoid conflicts
        file_ext = Path(original_filename).suffix
        unique_id = str(uuid.uuid4())[:8]
        return f"bot_{bot_id}/feedback_{feedback_id}_{unique_id}{file_ext}"
    
    async def upload_feedback_image(
        self, 
        image_data: bytes, 
        bot_id: int, 
        feedback_id: int, 
        original_filename: str
    ) -> Tuple[str, str]:
        """
        Upload feedback image to Azure Blob Storage with local fallback.
        
        Args:
            image_data: Binary image data
            bot_id: Bot ID for organization
            feedback_id: Feedback ID for organization
            original_filename: Original filename for content type detection
            
        Returns:
            Tuple of (storage_type, file_path_or_url)
        """
        blob_name = self._generate_blob_name(bot_id, feedback_id, original_filename)
        
        # Try Azure first if available
        if AZURE_AVAILABLE and self.blob_service_client:
            try:
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.settings.azure_container_name,
                    blob=blob_name
                )
                
                content_type = self._get_content_type(original_filename)
                content_settings = ContentSettings(content_type=content_type)
                
                blob_client.upload_blob(
                    image_data,
                    overwrite=True,
                    content_settings=content_settings
                )
                
                # Return Azure URL
                azure_url = blob_client.url
                logger.info(f"Image uploaded to Azure: {azure_url}")
                return ("azure", azure_url)
                
            except Exception as e:
                logger.error(f"Azure upload failed: {e}")
                # Fall back to local storage
        
        # Fallback to local storage
        local_file_path = self.local_dir / blob_name
        local_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(local_file_path, 'wb') as f:
            await f.write(image_data)
        
        logger.info(f"Image stored locally: {local_file_path}")
        return ("local", str(local_file_path))
    
    async def get_image_url(self, storage_type: str, file_path: str) -> str:
        """
        Get accessible URL for the image.
        
        Args:
            storage_type: "azure" or "local"
            file_path: File path or Azure URL
            
        Returns:
            Accessible URL for the image
        """
        if storage_type == "azure":
            return file_path  # Already a full URL
        elif storage_type == "local":
            # For local files, return relative path for serving via FastAPI static files
            try:
                rel_path = Path(file_path).relative_to(self.local_dir)
                return f"/static/feedback_images/{rel_path}"
            except ValueError:
                # If file_path is not relative to local_dir, return as-is
                return file_path
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")
    
    async def delete_image(self, storage_type: str, file_path: str) -> bool:
        """
        Delete image from storage.
        
        Args:
            storage_type: "azure" or "local"
            file_path: File path or Azure URL
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if storage_type == "azure" and AZURE_AVAILABLE and self.blob_service_client:
                # Extract blob name from URL
                blob_name = file_path.split('/')[-1]
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.settings.azure_container_name,
                    blob=blob_name
                )
                blob_client.delete_blob()
                logger.info(f"Deleted from Azure: {blob_name}")
                return True
                
            elif storage_type == "local":
                local_path = Path(file_path)
                if local_path.exists():
                    local_path.unlink()
                    logger.info(f"Deleted local file: {local_path}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error deleting image: {e}")
            
        return False


# Global storage manager instance
storage_manager = AzureStorageManager() 
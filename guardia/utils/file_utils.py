"""
Utility functions for file operations and management

This module provides file handling utilities for the Guardia AI system including:
- Image processing and manipulation
- Video file operations
- File system utilities
- Backup and cleanup operations
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
import hashlib
import mimetypes

try:
    import cv2
    import numpy as np
    from PIL import Image
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import aiofiles
    import aiofiles.os
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

logger = logging.getLogger(__name__)

class FileManager:
    """Async file operations manager"""
    
    def __init__(self, base_directory: str):
        self.base_directory = Path(base_directory)
        self.base_directory.mkdir(parents=True, exist_ok=True)
    
    async def save_file(self, content: bytes, filename: str, subdirectory: str = "") -> str:
        """
        Save file content to disk asynchronously
        
        Args:
            content: File content as bytes
            filename: Name of the file
            subdirectory: Optional subdirectory path
            
        Returns:
            str: Full path to saved file
        """
        try:
            file_path = self.base_directory / subdirectory / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(content)
            else:
                with open(file_path, 'wb') as f:
                    f.write(content)
            
            logger.info(f"Saved file: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save file {filename}: {str(e)}")
            raise

    async def read_file(self, filepath: str) -> bytes:
        """
        Read file content asynchronously
        
        Args:
            filepath: Path to file to read
            
        Returns:
            bytes: File content
        """
        try:
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(filepath, 'rb') as f:
                    return await f.read()
            else:
                with open(filepath, 'rb') as f:
                    return f.read()
                    
        except Exception as e:
            logger.error(f"Failed to read file {filepath}: {str(e)}")
            raise

    async def delete_file(self, filepath: str) -> bool:
        """
        Delete file asynchronously
        
        Args:
            filepath: Path to file to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if AIOFILES_AVAILABLE:
                await aiofiles.os.remove(filepath)
            else:
                os.remove(filepath)
            
            logger.info(f"Deleted file: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file {filepath}: {str(e)}")
            return False

    async def list_files(self, directory: str = "", pattern: str = "*") -> List[str]:
        """
        List files in directory matching pattern
        
        Args:
            directory: Directory to search (relative to base)
            pattern: File pattern to match
            
        Returns:
            List[str]: List of file paths
        """
        try:
            search_path = self.base_directory / directory
            files = list(search_path.glob(pattern))
            return [str(f) for f in files if f.is_file()]
            
        except Exception as e:
            logger.error(f"Failed to list files in {directory}: {str(e)}")
            return []

    def get_file_info(self, filepath: str) -> Dict[str, Any]:
        """
        Get file metadata and information
        
        Args:
            filepath: Path to file
            
        Returns:
            dict: File information
        """
        try:
            path = Path(filepath)
            stat = path.stat()
            
            return {
                "name": path.name,
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_ctime),
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "extension": path.suffix,
                "mime_type": mimetypes.guess_type(filepath)[0],
                "is_image": path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff'],
                "is_video": path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info for {filepath}: {str(e)}")
            return {}

class ImageProcessor:
    """Image processing utilities"""
    
    @staticmethod
    def resize_image(image_path: str, max_width: int = 1920, max_height: int = 1080, 
                    quality: int = 85) -> str:
        """
        Resize image while maintaining aspect ratio
        
        Args:
            image_path: Path to source image
            max_width: Maximum width
            max_height: Maximum height
            quality: JPEG quality (1-100)
            
        Returns:
            str: Path to resized image
        """
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available for image processing")
            return image_path
        
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Could not read image: {image_path}")
                return image_path
            
            # Get current dimensions
            height, width = img.shape[:2]
            
            # Calculate new dimensions
            if width > max_width or height > max_height:
                # Calculate scaling factor
                scale_w = max_width / width
                scale_h = max_height / height
                scale = min(scale_w, scale_h)
                
                new_width = int(width * scale)
                new_height = int(height * scale)
                
                # Resize image
                img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
                
                # Save resized image
                resized_path = image_path.replace('.', '_resized.')
                cv2.imwrite(resized_path, img, [cv2.IMWRITE_JPEG_QUALITY, quality])
                
                logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height}")
                return resized_path
            
            return image_path
            
        except Exception as e:
            logger.error(f"Failed to resize image {image_path}: {str(e)}")
            return image_path

    @staticmethod
    def create_thumbnail(image_path: str, size: Tuple[int, int] = (300, 300)) -> str:
        """
        Create thumbnail of image
        
        Args:
            image_path: Path to source image
            size: Thumbnail size (width, height)
            
        Returns:
            str: Path to thumbnail
        """
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available for thumbnail creation")
            return image_path
        
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                return image_path
            
            # Create thumbnail
            height, width = img.shape[:2]
            
            # Calculate aspect ratio
            aspect = width / height
            
            if aspect > 1:  # Landscape
                new_width = size[0]
                new_height = int(size[0] / aspect)
            else:  # Portrait
                new_height = size[1]
                new_width = int(size[1] * aspect)
            
            # Resize
            thumbnail = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # Save thumbnail
            thumbnail_path = image_path.replace('.', '_thumb.')
            cv2.imwrite(thumbnail_path, thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            return thumbnail_path
            
        except Exception as e:
            logger.error(f"Failed to create thumbnail for {image_path}: {str(e)}")
            return image_path

    @staticmethod
    def extract_frames_from_video(video_path: str, output_dir: str, 
                                 max_frames: int = 10) -> List[str]:
        """
        Extract frames from video file
        
        Args:
            video_path: Path to video file
            output_dir: Directory to save frames
            max_frames: Maximum number of frames to extract
            
        Returns:
            List[str]: Paths to extracted frames
        """
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available for video processing")
            return []
        
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return []
            
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Calculate frame intervals
            if total_frames <= max_frames:
                frame_interval = 1
            else:
                frame_interval = total_frames // max_frames
            
            # Extract frames
            frame_paths = []
            frame_count = 0
            current_frame = 0
            
            os.makedirs(output_dir, exist_ok=True)
            
            while cap.isOpened() and frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if current_frame % frame_interval == 0:
                    # Save frame
                    frame_filename = f"frame_{frame_count:04d}.jpg"
                    frame_path = os.path.join(output_dir, frame_filename)
                    cv2.imwrite(frame_path, frame)
                    frame_paths.append(frame_path)
                    frame_count += 1
                
                current_frame += 1
            
            cap.release()
            logger.info(f"Extracted {len(frame_paths)} frames from {video_path}")
            return frame_paths
            
        except Exception as e:
            logger.error(f"Failed to extract frames from {video_path}: {str(e)}")
            return []

class BackupManager:
    """Backup and recovery utilities"""
    
    def __init__(self, backup_directory: str):
        self.backup_directory = Path(backup_directory)
        self.backup_directory.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, source_dir: str, backup_name: Optional[str] = None) -> str:
        """
        Create compressed backup of directory
        
        Args:
            source_dir: Directory to backup
            backup_name: Optional backup name
            
        Returns:
            str: Path to backup file
        """
        try:
            if backup_name is None:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_path = self.backup_directory / f"{backup_name}.tar.gz"
            
            # Create tar.gz backup
            shutil.make_archive(
                str(backup_path.with_suffix('')),
                'gztar',
                source_dir
            )
            
            logger.info(f"Created backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            raise

    def restore_backup(self, backup_path: str, restore_dir: str) -> bool:
        """
        Restore backup to directory
        
        Args:
            backup_path: Path to backup file
            restore_dir: Directory to restore to
            
        Returns:
            bool: True if successful
        """
        try:
            # Extract backup
            shutil.unpack_archive(backup_path, restore_dir)
            
            logger.info(f"Restored backup {backup_path} to {restore_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {str(e)}")
            return False

    def cleanup_old_backups(self, days_to_keep: int = 30) -> int:
        """
        Remove backups older than specified days
        
        Args:
            days_to_keep: Number of days to keep backups
            
        Returns:
            int: Number of backups removed
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            removed_count = 0
            
            for backup_file in self.backup_directory.glob("backup_*.tar.gz"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    removed_count += 1
                    logger.info(f"Removed old backup: {backup_file}")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {str(e)}")
            return 0

def calculate_file_hash(filepath: str, algorithm: str = "md5") -> str:
    """
    Calculate hash of file
    
    Args:
        filepath: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)
        
    Returns:
        str: File hash
    """
    try:
        hash_func = hashlib.new(algorithm)
        
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
        
    except Exception as e:
        logger.error(f"Failed to calculate hash for {filepath}: {str(e)}")
        return ""

def get_directory_size(directory: str) -> Dict[str, Any]:
    """
    Calculate directory size and file count
    
    Args:
        directory: Path to directory
        
    Returns:
        dict: Directory statistics
    """
    try:
        total_size = 0
        file_count = 0
        
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
                    file_count += 1
        
        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2),
            "file_count": file_count
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate directory size for {directory}: {str(e)}")
        return {"total_size_bytes": 0, "total_size_mb": 0, "total_size_gb": 0, "file_count": 0}

def cleanup_temporary_files(temp_directory: str, max_age_hours: int = 24) -> int:
    """
    Clean up temporary files older than specified age
    
    Args:
        temp_directory: Path to temporary directory
        max_age_hours: Maximum age in hours
        
    Returns:
        int: Number of files removed
    """
    try:
        if not os.path.exists(temp_directory):
            return 0
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        removed_count = 0
        
        for root, dirs, files in os.walk(temp_directory):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_time < cutoff_time:
                        os.remove(filepath)
                        removed_count += 1
                        logger.debug(f"Removed temporary file: {filepath}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {filepath}: {str(e)}")
        
        return removed_count
        
    except Exception as e:
        logger.error(f"Failed to cleanup temporary files: {str(e)}")
        return 0

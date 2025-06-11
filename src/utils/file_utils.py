"""
File utility functions for Guardia AI
"""
import os
import shutil
from pathlib import Path
from typing import List, Tuple

def get_directory_size(path: str) -> Tuple[int, int]:
    """
    Get directory size and file count
    Returns: (size_in_bytes, file_count)
    """
    total_size = 0
    file_count = 0
    
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
                file_count += 1
            except (OSError, FileNotFoundError):
                pass
    
    return total_size, file_count

def format_size(size_bytes: int) -> str:
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def find_large_files(directory: str, min_size_mb: int = 10) -> List[Tuple[str, int]]:
    """Find files larger than specified size"""
    large_files = []
    min_size_bytes = min_size_mb * 1024 * 1024
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                size = os.path.getsize(filepath)
                if size > min_size_bytes:
                    large_files.append((filepath, size))
            except (OSError, FileNotFoundError):
                pass
    
    return sorted(large_files, key=lambda x: x[1], reverse=True)

def cleanup_empty_directories(directory: str) -> int:
    """Remove empty directories and return count"""
    removed_count = 0
    
    for root, dirs, files in os.walk(directory, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    removed_count += 1
            except (OSError, FileNotFoundError):
                pass
    
    return removed_count

def get_file_count_by_extension(directory: str) -> dict:
    """Get file count grouped by extension"""
    extension_counts = {}
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            _, ext = os.path.splitext(file)
            ext = ext.lower()
            extension_counts[ext] = extension_counts.get(ext, 0) + 1
    
    return extension_counts

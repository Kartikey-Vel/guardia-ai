"""
Cleanup utilities for Guardia AI
"""
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from .file_utils import get_directory_size, format_size

class ProjectCleanup:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        
    def analyze_project_size(self):
        """Analyze project size and file distribution"""
        print("🔍 Analyzing project size...")
        
        directories_to_check = [
            "data", "encodings", "faces", "detected", 
            "logs", "images", "__pycache__", ".git"
        ]
        
        total_size = 0
        total_files = 0
        
        for directory in directories_to_check:
            dir_path = self.project_root / directory
            if dir_path.exists():
                size, count = get_directory_size(str(dir_path))
                total_size += size
                total_files += count
                print(f"📁 {directory}: {format_size(size)} ({count} files)")
        
        print(f"\n📊 Total: {format_size(total_size)} ({total_files} files)")
        
        if total_files > 5000:
            print("⚠️  Large file count detected! Consider cleaning up.")
            
        return total_size, total_files
    
    def clean_detection_cache(self, days_old: int = 7):
        """Clean old detection files"""
        print(f"🧹 Cleaning detection files older than {days_old} days...")
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        removed_count = 0
        
        detected_dir = self.project_root / "detected"
        if detected_dir.exists():
            for file_path in detected_dir.rglob("*.*"):
                try:
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_date:
                        file_path.unlink()
                        removed_count += 1
                except (OSError, FileNotFoundError):
                    pass
        
        print(f"🗑️  Removed {removed_count} old detection files")
        return removed_count
    
    def clean_logs(self, max_size_mb: int = 50):
        """Clean log files if they exceed size limit"""
        print(f"🧹 Cleaning logs larger than {max_size_mb}MB...")
        
        logs_dir = self.project_root / "logs"
        if not logs_dir.exists():
            return 0
            
        removed_count = 0
        max_size_bytes = max_size_mb * 1024 * 1024
        
        for log_file in logs_dir.glob("*.log"):
            try:
                if log_file.stat().st_size > max_size_bytes:
                    # Keep last 1000 lines
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                    
                    if len(lines) > 1000:
                        with open(log_file, 'w') as f:
                            f.writelines(lines[-1000:])
                        removed_count += 1
            except (OSError, FileNotFoundError):
                pass
        
        print(f"🗑️  Trimmed {removed_count} large log files")
        return removed_count
    
    def clean_temp_files(self):
        """Clean temporary files"""
        print("🧹 Cleaning temporary files...")
        
        temp_patterns = [
            "**/*.tmp", "**/*.temp", "**/*~", 
            "**/.DS_Store", "**/Thumbs.db",
            "**/__pycache__", "**/*.pyc"
        ]
        
        removed_count = 0
        
        for pattern in temp_patterns:
            for file_path in self.project_root.glob(pattern):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        removed_count += 1
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                        removed_count += 1
                except (OSError, FileNotFoundError):
                    pass
        
        print(f"🗑️  Removed {removed_count} temporary files")
        return removed_count
    
    def full_cleanup(self):
        """Perform comprehensive cleanup"""
        print("🧹 Starting full project cleanup...")
        
        # Analyze before cleanup
        before_size, before_files = self.analyze_project_size()
        
        # Perform cleanup
        self.clean_temp_files()
        self.clean_detection_cache()
        self.clean_logs()
        
        # Analyze after cleanup
        print("\n📊 After cleanup:")
        after_size, after_files = self.analyze_project_size()
        
        # Show savings
        saved_size = before_size - after_size
        saved_files = before_files - after_files
        
        print(f"\n✅ Cleanup complete!")
        print(f"💾 Space saved: {format_size(saved_size)}")
        print(f"📄 Files removed: {saved_files}")
        
        return saved_size, saved_files

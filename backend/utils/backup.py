"""
TASK-077: Database Backup Utility
===================================
Creates timestamped SQLite backups using SQLite's online backup API.

Usage (CLI):
    python backup.py                    # backup guardia.db → backups/
    python backup.py --max-backups 7    # keep only last 7 backups
    python backup.py --db-path /path/to/guardia.db

Usage (from code):
    from utils.backup import BackupManager
    manager = BackupManager()
    path = manager.create_backup()
    print(f"Backed up to: {path}")
"""

import logging
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class BackupManager:
    """
    Manages SQLite database backups using the native SQLite backup API.
    Backups are stored as guardia_YYYYMMDD_HHMMSS.db in the backup directory.
    """

    def __init__(
        self,
        db_path: str = "./guardia.db",
        backup_dir: str = "./backups",
        max_backups: int = 10,
    ) -> None:
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> Optional[str]:
        """
        Create a backup of the SQLite database using the online backup API.

        Returns the path of the created backup file, or None on failure.
        """
        if not self.db_path.exists():
            logger.warning("Database file not found: %s", self.db_path)
            return None

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"guardia_{timestamp}.db"
        backup_path = self.backup_dir / backup_filename

        try:
            # Use SQLite's built-in online backup API (safe even while DB is being written)
            source = sqlite3.connect(str(self.db_path))
            dest = sqlite3.connect(str(backup_path))
            source.backup(dest)
            dest.close()
            source.close()

            size_kb = backup_path.stat().st_size / 1024
            logger.info(
                "Backup created: %s (%.1f KB)", backup_path, size_kb
            )
            self._prune_old_backups()
            return str(backup_path)

        except Exception as exc:
            logger.error("Backup failed: %s", exc)
            if backup_path.exists():
                backup_path.unlink(missing_ok=True)
            return None

    def list_backups(self) -> list[dict]:
        """Return metadata for all existing backups, newest first."""
        backups = sorted(
            self.backup_dir.glob("guardia_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return [
            {
                "filename": p.name,
                "path": str(p),
                "size_kb": round(p.stat().st_size / 1024, 1),
                "created_at": datetime.utcfromtimestamp(p.stat().st_mtime).isoformat() + "Z",
            }
            for p in backups
        ]

    def restore_backup(self, backup_filename: str) -> bool:
        """Restore the database from a named backup file."""
        backup_path = self.backup_dir / backup_filename
        if not backup_path.exists():
            logger.error("Backup file not found: %s", backup_path)
            return False
        try:
            shutil.copy2(str(backup_path), str(self.db_path))
            logger.info("Restored database from: %s", backup_path)
            return True
        except Exception as exc:
            logger.error("Restore failed: %s", exc)
            return False

    def _prune_old_backups(self) -> None:
        """Remove oldest backups when count exceeds max_backups."""
        backups = sorted(
            self.backup_dir.glob("guardia_*.db"),
            key=lambda p: p.stat().st_mtime,
        )
        while len(backups) > self.max_backups:
            oldest = backups.pop(0)
            oldest.unlink(missing_ok=True)
            logger.info("Pruned old backup: %s", oldest.name)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

backup_manager = BackupManager()

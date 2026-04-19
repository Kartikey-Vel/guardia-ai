"""
TASK-077: Database Backup CLI
==============================
Standalone backup script — run from the backend directory.

Usage:
    python backup.py                    # create backup to ./backups/
    python backup.py --list             # list existing backups
    python backup.py --restore <file>   # restore from backup file
    python backup.py --max-backups 7    # keep only 7 backups
    python backup.py --db-path /custom/path/guardia.db
"""

import argparse
import sys
from pathlib import Path

# Ensure the backend directory is on the path
sys.path.insert(0, str(Path(__file__).parent))

from utils.backup import BackupManager
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Guardia AI — SQLite database backup utility"
    )
    parser.add_argument("--db-path", default="./guardia.db", help="Path to guardia.db")
    parser.add_argument("--backup-dir", default="./backups", help="Backup directory")
    parser.add_argument("--max-backups", type=int, default=10, help="Max backups to keep")
    parser.add_argument("--list", action="store_true", help="List existing backups")
    parser.add_argument("--restore", metavar="FILENAME", help="Restore from backup file")

    args = parser.parse_args()

    manager = BackupManager(
        db_path=args.db_path,
        backup_dir=args.backup_dir,
        max_backups=args.max_backups,
    )

    if args.list:
        backups = manager.list_backups()
        if not backups:
            print("No backups found.")
            return
        print(f"{'Filename':<35} {'Size':>8}  {'Created'}")
        print("-" * 70)
        for b in backups:
            print(f"{b['filename']:<35} {b['size_kb']:>6.1f}KB  {b['created_at']}")
        print(f"\n{len(backups)} backup(s) in {args.backup_dir}")
        return

    if args.restore:
        ok = manager.restore_backup(args.restore)
        sys.exit(0 if ok else 1)

    # Default: create backup
    path = manager.create_backup()
    if path:
        print(f"✅ Backup created: {path}")
        sys.exit(0)
    else:
        print("❌ Backup failed. Check logs.")
        sys.exit(1)


if __name__ == "__main__":
    main()

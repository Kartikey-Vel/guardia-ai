#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dataset Fetcher for Guardia-AI (Home/Personal Security + Disaster/Theft)

This script organizes a separate datasets folder and attempts to download
as many sources as possible automatically. For datasets that require
manual access or credentials, it scaffolds folders and writes clear
instructions with the official links so you can fetch them safely.

Supported sources out of the box:
- Direct GitHub ZIPs (DeepFireSmoke, VisiFire, ESC-50)
- COCO 2017 (optional, large)
- WIDER FACE (optional; direct links, may be slow)
- Open Images V6 filtered classes via downloader.py (optional)
- Kaggle datasets (optional; requires Kaggle API configured)

Outputs:
- datasets/external/<dataset_slug>/ ... files ...
- datasets/_manifest.json with per-dataset status
- per-dataset README.txt with license/source/instructions when manual steps are needed

Usage (Windows PowerShell examples):
  # Dry-run to see what will be created
  python scripts/fetch_datasets.py --dry-run

  # Download auto sources into datasets/external
  python scripts/fetch_datasets.py

  # Include heavy datasets (COCO, WIDER)
  python scripts/fetch_datasets.py --include-heavy

  # Use Open Images downloader (requires downloader.py in repo root) for selected classes
  python scripts/fetch_datasets.py --openimages-classes "person,backpack,handbag,suitcase,cell phone,knife"

  # Enable Kaggle downloads if you have ~/.kaggle/kaggle.json set up
  python scripts/fetch_datasets.py --use-kaggle

Notes:
- Respect dataset licenses and terms. This script avoids scraping gated content.
- For manual datasets, follow the printed instructions and README.txt in each folder.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import zipfile
import subprocess
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional

try:
    from urllib.request import urlopen, Request
except Exception:
    import urllib.request
    urlopen = urllib.request.urlopen  # type: ignore
    Request = urllib.request.Request  # type: ignore


# ----------------------------
# Configurable dataset catalog
# ----------------------------

def dataset_catalog(include_heavy: bool) -> List[Dict]:
    """Return a list of dataset entries with download strategies.

    Each entry has:
      - slug: folder name under datasets/external
      - name: human-friendly label
      - category: short tag
      - method: one of [direct_zip, multi_zip, openimages, kaggle, manual]
      - urls / items / slug specifics depending on method
    """
    items: List[Dict] = [
        # Fire/Smoke (GitHub ZIPs)
        {
            "slug": "deepfiresmoke",
            "name": "DeepFireSmoke (GitHub)",
            "category": "fire-smoke",
            "method": "direct_zip",
            "url": "https://codeload.github.com/DeepQuestAI/Fire-Smoke-Dataset/zip/refs/heads/master",
            "filename": "DeepFireSmoke.zip",
            "license": "Refer to repo LICENSE",
            "source": "https://github.com/DeepQuestAI/Fire-Smoke-Dataset",
        },
        {
            "slug": "visifire",
            "name": "VisiFire (GitHub)",
            "category": "fire-smoke",
            "method": "direct_zip",
            "url": "https://codeload.github.com/OlafenwaMoses/VisiFire/zip/refs/heads/master",
            "filename": "VisiFire.zip",
            "license": "Refer to repo LICENSE",
            "source": "https://github.com/OlafenwaMoses/VisiFire",
        },
        # Audio examples
        {
            "slug": "esc50",
            "name": "ESC-50 (GitHub)",
            "category": "audio",
            "method": "direct_zip",
            "url": "https://codeload.github.com/karoldvl/ESC-50/zip/refs/heads/master",
            "filename": "ESC-50.zip",
            "license": "Refer to repo LICENSE",
            "source": "https://github.com/karoldvl/ESC-50",
        },
        # Open Images (class-filtered) - optional via downloader.py
        {
            "slug": "openimages_filtered",
            "name": "Open Images V6 (class-filtered)",
            "category": "general-od",
            "method": "openimages",
            "source": "https://storage.googleapis.com/openimages/web/download.html",
            "notes": "Requires downloader.py in repo root. Provide --openimages-classes.",
        },
        # Kaggle examples (optional)
        {
            "slug": "kaggle_water_leak_images",
            "name": "Kaggle: Water Leak Images",
            "category": "disaster-water",
            "method": "kaggle",
            "kaggle_slug": "ismailpromus/water-leak-images",
            "source": "https://www.kaggle.com/datasets/ismailpromus/water-leak-images",
        },
        {
            "slug": "kaggle_pipe_leak_detection",
            "name": "Kaggle: Pipe Leak Detection",
            "category": "disaster-water",
            "method": "kaggle",
            "kaggle_slug": "naveengowda16/leak-detection",
            "source": "https://www.kaggle.com/datasets/naveengowda16/leak-detection",
        },
        # Manual-only datasets: scaffold + instructions
        {
            "slug": "ucf_crime",
            "name": "UCF-Crime",
            "category": "intrusion-theft",
            "method": "manual",
            "source": "https://www.crcv.ucf.edu/projects/real-world/",
            "why": "Burglary/robbery/stealing/shoplifting categories",
        },
        {
            "slug": "virat",
            "name": "VIRAT Video Dataset",
            "category": "intrusion-theft",
            "method": "manual",
            "source": "https://viratdata.org/",
            "why": "Surveillance actions, people/vehicles/carrying",
        },
        {
            "slug": "shanghaitech_campus",
            "name": "ShanghaiTech Campus",
            "category": "anomaly",
            "method": "manual",
            "source": "https://svip-lab.github.io/datasets/campus_dataset.html",
            "why": "Anomaly detection in crowds",
        },
        {
            "slug": "avenue",
            "name": "CUHK Avenue",
            "category": "anomaly",
            "method": "manual",
            "source": "http://www.cse.cuhk.edu.hk/leojia/projects/detectabnormal/dataset.html",
            "why": "Abnormal events in surveillance videos",
        },
        {
            "slug": "ucsd_ped",
            "name": "UCSD Ped1/Ped2",
            "category": "anomaly",
            "method": "manual",
            "source": "http://www.svcl.ucsd.edu/projects/anomaly/dataset.htm",
            "why": "Crowd anomalies / loiter-like patterns",
        },
        {
            "slug": "urbansound8k",
            "name": "UrbanSound8K",
            "category": "audio",
            "method": "manual",
            "source": "https://urbansounddataset.weebly.com/urbansound8k.html",
            "why": "Sirens, dog bark, glass break, etc.",
        },
        {
            "slug": "wider_face",
            "name": "WIDER FACE",
            "category": "faces",
            "method": "multi_zip" if include_heavy else "manual",
            "source": "http://shuoyang1213.me/WIDERFACE/",
            "why": "Faces with occlusions/poses",
            "items": [
                {
                    "url": "http://shuoyang1213.me/WIDERFACE/WIDER_train.zip",
                    "filename": "WIDER_train.zip",
                },
                {
                    "url": "http://shuoyang1213.me/WIDERFACE/WIDER_val.zip",
                    "filename": "WIDER_val.zip",
                },
                {
                    "url": "http://shuoyang1213.me/WIDERFACE/wider_face_split.zip",
                    "filename": "wider_face_split.zip",
                },
            ],
        },
    ]

    if include_heavy:
        items.extend(
            [
                {
                    "slug": "coco2017",
                    "name": "MS COCO 2017",
                    "category": "general-od",
                    "method": "multi_zip",
                    "source": "https://cocodataset.org/#download",
                    "why": "Baseline for person/backpack/cellphone/dog",
                    "items": [
                        {
                            "url": "http://images.cocodataset.org/zips/train2017.zip",
                            "filename": "train2017.zip",
                        },
                        {
                            "url": "http://images.cocodataset.org/zips/val2017.zip",
                            "filename": "val2017.zip",
                        },
                        {
                            "url": "http://images.cocodataset.org/annotations/annotations_trainval2017.zip",
                            "filename": "annotations_trainval2017.zip",
                        },
                    ],
                }
            ]
        )

    return items


# ----------------------------
# Utilities
# ----------------------------

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def human_size(n: float) -> str:
    sz = float(n)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if sz < 1024:
            return f"{sz:.1f} {unit}" if unit != "B" else f"{int(sz)} {unit}"
        sz /= 1024.0
    return f"{sz:.1f} PB"


def http_download(url: str, out_path: Path, user_agent: str = "guardia-ai-fetcher/1.0") -> None:
    req = Request(url, headers={"User-Agent": user_agent})
    with urlopen(req) as r:  # type: ignore
        total = int(r.headers.get("Content-Length", 0))
        chunk = 1024 * 1024
        downloaded = 0
        start = time.time()
        with open(out_path, "wb") as f:
            while True:
                data = r.read(chunk)
                if not data:
                    break
                f.write(data)
                downloaded += len(data)
                if total:
                    pct = downloaded * 100.0 / total
                    rate = downloaded / max(1e-6, (time.time() - start))
                    sys.stdout.write(
                        f"\r  -> {out_path.name}: {pct:5.1f}% ({human_size(downloaded)}/{human_size(total)}) @ {human_size(int(rate))}/s"
                    )
                    sys.stdout.flush()
        if total:
            sys.stdout.write("\n")


def extract_zip(zip_path: Path, dest_dir: Path) -> None:
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(dest_dir)
    except zipfile.BadZipFile:
        print(f"[WARN] Not a ZIP or corrupted: {zip_path}")


def maybe_open_browser(url: str, auto_open: bool) -> None:
    if auto_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass


# ----------------------------
# Methods
# ----------------------------

def handle_direct_zip(entry: Dict, dest: Path, extract: bool, dry_run: bool, manifest: Dict) -> None:
    ensure_dir(dest)
    url = entry["url"]
    filename = entry.get("filename", Path(url).name)
    zip_path = dest / filename
    if dry_run:
        print(f"[DRY] Would download: {url} -> {zip_path}")
        manifest[entry["slug"]] = {"status": "dry-run", "url": url}
        return
    print(f"[GET] {entry['name']} → {zip_path}")
    http_download(url, zip_path)
    if extract:
        print(f"[UNZIP] {zip_path} → {dest}")
        extract_zip(zip_path, dest)
    manifest[entry["slug"]] = {"status": "ok", "download": str(zip_path)}


def handle_multi_zip(entry: Dict, dest: Path, extract: bool, dry_run: bool, manifest: Dict) -> None:
    ensure_dir(dest)
    results = []
    for it in entry.get("items", []):
        url = it["url"]
        filename = it.get("filename", Path(url).name)
        zip_path = dest / filename
        if dry_run:
            print(f"[DRY] Would download: {url} -> {zip_path}")
            results.append({"url": url, "status": "dry-run"})
            continue
        print(f"[GET] {entry['name']} part → {zip_path}")
        http_download(url, zip_path)
        if extract:
            print(f"[UNZIP] {zip_path} → {dest}")
            extract_zip(zip_path, dest)
        results.append({"url": url, "path": str(zip_path)})
    manifest[entry["slug"]] = {"status": "ok", "parts": results}


def _normalize_openimages_classes(classes: List[str]) -> List[str]:
    # Map common synonyms and fix capitalization for Open Images
    synonyms = {
        "cell phone": "Mobile phone",
        "cellphone": "Mobile phone",
        "mobile": "Mobile phone",
        "mobile phone": "Mobile phone",
        "smartphone": "Mobile phone",
        "person": "Person",
        "backpack": "Backpack",
        "handbag": "Handbag",
        "suitcase": "Suitcase",
        "knife": "Knife",
        "dog": "Dog",
        "cat": "Cat",
    }
    normalized: List[str] = []
    for c in classes:
        k = c.strip().lower()
        normalized.append(synonyms.get(k, c.strip().title()))
    return normalized


def handle_openimages(entry: Dict, dest: Path, classes: List[str], dry_run: bool, manifest: Dict, limit: Optional[int] = None) -> None:
    ensure_dir(dest)
    if not classes:
        print(f"[SKIP] {entry['name']}: no classes provided. Use --openimages-classes.")
        manifest[entry["slug"]] = {"status": "skipped", "reason": "no-classes"}
        return
    # Try local downloader.py if present; otherwise fall back to PyPI 'openimages' API
    repo_root = Path(__file__).resolve().parents[1]
    dl_py = repo_root / "downloader.py"
    if dry_run:
        if dl_py.exists():
            print(
                f"[DRY] Would run: {sys.executable} {dl_py} --download_folder {dest} --classes {' '.join(classes)}"
            )
        else:
            print(
                f"[DRY] Would call openimages.download.download_dataset(dest_dir={dest}, class_labels={_normalize_openimages_classes(classes)}, annotation_format='darknet', limit={limit if limit and limit>0 else 'unlimited'})"
            )
        manifest[entry["slug"]] = {"status": "dry-run", "classes": classes}
        return

    if dl_py.exists():
        print(f"[RUN] Open Images downloader (local) for classes: {classes}")
        cmd = [
            sys.executable,
            str(dl_py),
            "--download_folder",
            str(dest),
            "--classes",
            *classes,
        ]
        try:
            subprocess.check_call(cmd)
            manifest[entry["slug"]] = {"status": "ok", "classes": classes, "method": "downloader.py"}
            return
        except subprocess.CalledProcessError as e:
            print(f"[WARN] Local downloader.py failed ({e}); falling back to PyPI openimages API.")

    # Fallback: PyPI openimages API with YOLO (Darknet) labels
    try:
        from openimages import download as oid_download
        norm = _normalize_openimages_classes(classes)
        print(f"[RUN] openimages.download.download_dataset → {dest} classes={norm} limit={limit if limit and limit>0 else 'unlimited'}")
        kwargs: Dict[str, object] = dict(dest_dir=str(dest), class_labels=norm, annotation_format="darknet", csv_dir=str(dest / "_meta"))
        if limit and limit > 0:
            kwargs["limit"] = limit
        oid_download.download_dataset(**kwargs)  # type: ignore[arg-type]
        manifest[entry["slug"]] = {"status": "ok", "classes": norm, "method": "openimages-pypi", "limit": limit if limit and limit>0 else None}
    except Exception as e:
        print(f"[ERR] openimages API failed: {e}")
        manifest[entry["slug"]] = {"status": "error", "error": str(e)}


def handle_kaggle(entry: Dict, dest: Path, use_kaggle: bool, dry_run: bool, manifest: Dict) -> None:
    ensure_dir(dest)
    slug = entry["kaggle_slug"]
    if not use_kaggle:
        print(f"[SKIP] {entry['name']}: Kaggle disabled. Use --use-kaggle to enable.")
        manifest[entry["slug"]] = {"status": "skipped", "reason": "kaggle-disabled"}
        return
    try:
        import importlib.util as _ilu
        if _ilu.find_spec("kaggle") is None:
            raise ImportError
    except ImportError:
        print("[SKIP] Kaggle API not installed or configured. pip install kaggle and place kaggle.json in %USERPROFILE%/.kaggle/")
        manifest[entry["slug"]] = {"status": "skipped", "reason": "kaggle-not-installed"}
        return
    if dry_run:
        print(f"[DRY] Would run Kaggle download: {slug} → {dest}")
        manifest[entry["slug"]] = {"status": "dry-run", "kaggle": slug}
        return
    print(f"[KG] Downloading Kaggle dataset: {slug}")
    cmd = [
        sys.executable,
        "-m",
        "kaggle",
        "datasets",
        "download",
        "-d",
        slug,
        "-p",
        str(dest),
        "-q",
    ]
    try:
        subprocess.check_call(cmd)
        for z in dest.glob("*.zip"):
            print(f"[UNZIP] {z} → {dest}")
            extract_zip(z, dest)
        manifest[entry["slug"]] = {"status": "ok", "kaggle": slug}
    except subprocess.CalledProcessError as e:
        print(f"[ERR] Kaggle download failed: {e}")
        manifest[entry["slug"]] = {"status": "error", "error": str(e)}


def handle_manual(entry: Dict, dest: Path, auto_open: bool, manifest: Dict) -> None:
    ensure_dir(dest)
    info = [
        f"Name: {entry['name']}",
        f"Category: {entry.get('category', '')}",
        f"Source: {entry.get('source', '')}",
        f"Why: {entry.get('why', '')}",
        "",
        "This dataset requires manual access or acceptance of terms.",
        "1) Open the source link above",
        "2) Follow instructions to request/download",
        "3) Place the files under this folder",
    ]
    write_text(dest / "README.txt", "\n".join(info))
    maybe_open_browser(entry.get("source", ""), auto_open)
    manifest[entry["slug"]] = {"status": "manual", "source": entry.get("source")}


# ----------------------------
# Main
# ----------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch prioritized datasets into a separate folder")
    parser.add_argument("--root", default="datasets/external", help="Root output folder for datasets")
    parser.add_argument("--include-heavy", action="store_true", help="Include heavy datasets like COCO/WIDER")
    parser.add_argument(
        "--openimages-classes",
        default="",
        help="Comma-separated classes for Open Images (requires downloader.py)",
    )
    parser.add_argument(
        "--openimages-limit",
        type=int,
        default=0,
        help="Max images per class for Open Images (0 = unlimited)",
    )
    parser.add_argument("--use-kaggle", action="store_true", help="Enable Kaggle downloads (requires setup)")
    parser.add_argument("--extract", action="store_true", help="Extract downloaded ZIPs where applicable")
    parser.add_argument("--dry-run", action="store_true", help="Plan only; do not download")
    parser.add_argument("--open-browser", action="store_true", help="Open manual dataset pages in browser")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    ensure_dir(root)
    manifest_path = root.parent / "_manifest.json"
    manifest: Dict[str, Dict] = {}

    classes = [c.strip() for c in args.openimages_classes.split(",") if c.strip()] if args.openimages_classes else []

    print(f"[INIT] Output root: {root}")
    entries = dataset_catalog(include_heavy=args.include_heavy)
    for entry in entries:
        slug = entry["slug"]
        dest = root / slug
        name = entry["name"]
        method = entry["method"]
        print(f"\n=== {name} ({slug}) :: {method} ===")
        try:
            if method == "direct_zip":
                handle_direct_zip(entry, dest, extract=args.extract, dry_run=args.dry_run, manifest=manifest)
            elif method == "multi_zip":
                handle_multi_zip(entry, dest, extract=args.extract, dry_run=args.dry_run, manifest=manifest)
            elif method == "openimages":
                handle_openimages(entry, dest, classes=classes, dry_run=args.dry_run, manifest=manifest, limit=int(args.openimages_limit) if getattr(args, 'openimages_limit', 0) else None)
            elif method == "kaggle":
                handle_kaggle(entry, dest, use_kaggle=args.use_kaggle, dry_run=args.dry_run, manifest=manifest)
            elif method == "manual":
                handle_manual(entry, dest, auto_open=args.open_browser, manifest=manifest)
            else:
                print(f"[WARN] Unknown method: {method}")
                manifest[slug] = {"status": "unknown-method", "method": method}
        except Exception as e:
            print(f"[ERR] Failed {name}: {e}")
            manifest[slug] = {"status": "error", "error": str(e)}

    # Save manifest next to root as datasets/_manifest.json
    ensure_dir(manifest_path.parent)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n[DONE] Manifest written: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

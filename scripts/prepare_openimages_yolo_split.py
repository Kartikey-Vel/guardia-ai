import os
import shutil
import hashlib
from pathlib import Path


def slugify(name: str) -> str:
    return ''.join(c for c in name.lower().replace(' ', '_') if c.isalnum() or c in ('_', '-'))


def deterministic_split(key: str, train_ratio: float = 0.9) -> str:
    h = hashlib.sha1(key.encode('utf-8')).hexdigest()
    v = int(h[:8], 16) / 0xFFFFFFFF
    return 'train' if v < train_ratio else 'val'


def main():
    base = Path('datasets') / 'external' / 'openimages_filtered'
    if not base.exists():
        print('[error] base folder not found:', base)
        return 1

    # Create aggregated folders
    agg_images = base / 'images'
    agg_labels = base / 'labels'
    for split in ('train', 'val'):
        (agg_images / split).mkdir(parents=True, exist_ok=True)
        (agg_labels / split).mkdir(parents=True, exist_ok=True)

    # Discover class folders (exclude meta and files)
    class_dirs = []
    for entry in base.iterdir():
        if entry.is_dir() and entry.name not in {'images', 'labels', '_meta'}:
            class_dirs.append(entry)

    moved = 0
    skipped = 0
    for cdir in class_dirs:
        class_name = cdir.name
        img_dir = cdir / 'images'
        lbl_dir = cdir / 'darknet'
        if not img_dir.exists() or not lbl_dir.exists():
            print('[warn] missing images/darknet in', cdir)
            continue

        class_slug = slugify(class_name)
        for img_path in img_dir.glob('*.jpg'):
            stem = img_path.stem
            lbl_path = lbl_dir / f'{stem}.txt'
            if not lbl_path.exists():
                skipped += 1
                continue

            # Determine split deterministically
            split = deterministic_split(f'{class_slug}/{stem}')
            out_img = agg_images / split / f'{class_slug}_{stem}.jpg'
            out_lbl = agg_labels / split / f'{class_slug}_{stem}.txt'

            # Copy (not move) to keep source intact
            if not out_img.exists():
                shutil.copy2(img_path, out_img)
            if not out_lbl.exists():
                shutil.copy2(lbl_path, out_lbl)
            moved += 1

    # Ensure dataset.yaml exists with correct paths
    dataset_yaml = base / 'dataset.yaml'
    if not dataset_yaml.exists():
        print('[info] creating dataset.yaml')
    names_file = base / 'darknet_obj_names.txt'
    names = []
    if names_file.exists():
        with names_file.open('r', encoding='utf-8') as f:
            for line in f:
                n = line.strip()
                if n:
                    names.append(n)
    content = 'path: .\ntrain: images/train\nval: images/val\nnames:\n'
    if names:
        for i, n in enumerate(names):
            content += f"  {i}: {n}\n"
    dataset_yaml.write_text(content, encoding='utf-8')

    print(f'[ok] Prepared dataset. Copied {moved} image/label pairs, skipped {skipped} without labels.')
    print('[hint] You can now train with scripts/train_openimages_custom.py --data datasets/external/openimages_filtered')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

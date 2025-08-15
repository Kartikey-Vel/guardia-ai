import argparse
import csv
import os
import random
import shutil
from typing import Dict, List, Tuple, Set

# This script converts Open Images V6 annotations to YOLO format
# Focused classes for home/personal security + theft: person, backpack, handbag, suitcase, cell phone, knife
# Usage (prepare annotations first):
#   python scripts/convert_openimages_to_yolo.py \
#       --annotations path/to/train-annotations-bbox.csv \
#       --class_desc path/to/class-descriptions-boxable.csv \
#       --images-root path/to/downloaded/images/train \
#       --out-dir datasets/home_security \
#       --classes "person,backpack,handbag,suitcase,cell phone,knife" \
#       --val-split 0.15

DEFAULT_CLASSES = [
    "person",
    "backpack",
    "handbag",
    "suitcase",
    "cell phone",
    "knife",
]


def load_class_map(class_desc_csv: str) -> Dict[str, str]:
    """Returns name->class_id mapping from class-descriptions-boxable.csv"""
    m: Dict[str, str] = {}
    with open(class_desc_csv, newline='', encoding='utf-8') as f:
        r = csv.reader(f)
        for row in r:
            if len(row) < 2:
                continue
            class_id, name = row[0].strip(), row[1].strip()
            m[name] = class_id
    return m


def ensure_dirs(base: str) -> Tuple[str, str, str, str]:
    images_train = os.path.join(base, 'images', 'train')
    images_val = os.path.join(base, 'images', 'val')
    labels_train = os.path.join(base, 'labels', 'train')
    labels_val = os.path.join(base, 'labels', 'val')
    for d in (images_train, images_val, labels_train, labels_val):
        os.makedirs(d, exist_ok=True)
    return images_train, images_val, labels_train, labels_val


def yolo_row(xmin: float, ymin: float, xmax: float, ymax: float) -> Tuple[float, float, float, float]:
    # OpenImages coords are absolute in [0,1]
    cx = (xmin + xmax) / 2.0
    cy = (ymin + ymax) / 2.0
    w = xmax - xmin
    h = ymax - ymin
    return cx, cy, w, h


def convert(
    annotations_csv: str,
    class_desc_csv: str,
    images_root: str,
    out_dir: str,
    class_names: List[str],
    val_split: float,
    copy_images: bool = True,
) -> None:
    name_to_id = load_class_map(class_desc_csv)
    wanted = [n.strip() for n in class_names if n.strip()] or DEFAULT_CLASSES
    missing = [n for n in wanted if n not in name_to_id]
    if missing:
        print(f"[warn] Some classes not found in class-descriptions: {missing}")
    id_to_index: Dict[str, int] = {}
    idx_names: List[str] = []
    for i, n in enumerate(wanted):
        cid = name_to_id.get(n)
        if cid:
            id_to_index[cid] = i
            idx_names.append(n)

    images_train, images_val, labels_train, labels_val = ensure_dirs(out_dir)

    # Aggregate boxes per image
    boxes: Dict[str, List[Tuple[int, float, float, float, float]]] = {}
    used_ids: Set[str] = set()
    with open(annotations_csv, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            cid = row.get('LabelName')
            if cid not in id_to_index:
                continue
            try:
                img_id = row['ImageID']
                xmin = float(row['XMin']); xmax = float(row['XMax'])
                ymin = float(row['YMin']); ymax = float(row['YMax'])
            except Exception:
                continue
            cx, cy, w, h = yolo_row(xmin, ymin, xmax, ymax)
            boxes.setdefault(img_id, []).append((id_to_index[cid], cx, cy, w, h))
            used_ids.add(img_id)

    ids = list(used_ids)
    random.shuffle(ids)
    split = int(len(ids) * (1.0 - val_split))
    train_ids = set(ids[:split])
    val_ids = set(ids[split:])

    def write_label(path_no_ext: str, rows: List[Tuple[int, float, float, float, float]]):
        with open(path_no_ext + '.txt', 'w', encoding='utf-8') as f:
            for (cls, cx, cy, w, h) in rows:
                f.write(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

    # Copy labels and images
    total_written = 0
    for img_id, rows in boxes.items():
        # image source
        src_jpg = os.path.join(images_root, f"{img_id}.jpg")
        src_png = os.path.join(images_root, f"{img_id}.png")
        src = src_jpg if os.path.exists(src_jpg) else (src_png if os.path.exists(src_png) else None)
        if img_id in train_ids:
            img_dst_dir, lab_dst_dir = images_train, labels_train
        else:
            img_dst_dir, lab_dst_dir = images_val, labels_val
        os.makedirs(img_dst_dir, exist_ok=True)
        os.makedirs(lab_dst_dir, exist_ok=True)
        # label path
        lab_path_no_ext = os.path.join(lab_dst_dir, img_id)
        write_label(lab_path_no_ext, rows)
        total_written += 1
        # image copy (optional)
        if copy_images and src:
            dst_img = os.path.join(img_dst_dir, os.path.basename(src))
            if not os.path.exists(dst_img):
                try:
                    shutil.copyfile(src, dst_img)
                except Exception:
                    pass

    # dataset.yaml
    yaml_path = os.path.join(out_dir, 'dataset.yaml')
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write("# Ultralytics YOLO dataset config\n")
        f.write(f"path: {os.path.abspath(out_dir).replace('\\\\','/')}\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        f.write(f"names: {idx_names}\n")

    print(f"[ok] Wrote {total_written} label files. Dataset at: {out_dir}")
    print(f"[ok] dataset.yaml -> {yaml_path}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser("Convert OpenImages to YOLO")
    ap.add_argument('--annotations', required=True)
    ap.add_argument('--class_desc', required=True)
    ap.add_argument('--images-root', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--classes', default=",".join(DEFAULT_CLASSES))
    ap.add_argument('--val-split', type=float, default=0.15)
    ap.add_argument('--no-copy-images', action='store_true')
    args = ap.parse_args()

    class_names = [c.strip() for c in args.classes.split(',') if c.strip()]
    convert(
        annotations_csv=args.annotations,
        class_desc_csv=args.class_desc,
        images_root=args.images_root,
        out_dir=args.out_dir,
        class_names=class_names,
        val_split=max(0.0, min(0.9, args.val_split)),
        copy_images=not args.no_copy_images,
    )

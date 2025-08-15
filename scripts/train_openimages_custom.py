import argparse
import os
from pathlib import Path


def find_dataset_yaml(base_dir: str) -> str | None:
    # Default location from our converter
    p = Path(base_dir) / 'dataset.yaml'
    if p.exists():
        return str(p)
    # Fallback: search under base
    for root, _dirs, files in os.walk(base_dir):
        if 'dataset.yaml' in files:
            return os.path.join(root, 'dataset.yaml')
    return None


def main():
    ap = argparse.ArgumentParser('Train YOLOv8 on converted OpenImages subset and export ONNX')
    ap.add_argument('--data', default=str(Path('datasets') / 'external' / 'openimages_filtered'))
    ap.add_argument('--model', default='yolov8n.pt')
    ap.add_argument('--epochs', type=int, default=10)
    ap.add_argument('--imgsz', type=int, default=640)
    ap.add_argument('--device', default='cpu')
    ap.add_argument('--project', default='runs')
    args = ap.parse_args()

    try:
        from ultralytics import YOLO  # type: ignore
    except Exception as ex:
        print('[error] ultralytics not installed:', ex)
        return

    data_yaml = find_dataset_yaml(args.data)
    if not data_yaml:
        print('[error] dataset.yaml not found under', args.data)
        return

    print('[train] data =', data_yaml)
    print('[train] model =', args.model)
    print('[train] epochs =', args.epochs, 'imgsz =', args.imgsz, 'device =', args.device)

    model = YOLO(args.model)
    try:
        if hasattr(model, 'to') and args.device and args.device != 'auto':
            model.to(args.device)
    except Exception:
        pass

    results = model.train(data=data_yaml, epochs=args.epochs, imgsz=args.imgsz, device=args.device, project=args.project)
    # Export best to ONNX
    try:
        exp_dir = None
        if results is not None and hasattr(results, 'save_dir') and getattr(results, 'save_dir'):
            exp_dir = str(getattr(results, 'save_dir'))
        if not exp_dir:
            exp_dir = getattr(model, 'save_dir', None) or args.project
        # Must point to best.pt for export
        best_pt = None
        for root, _dirs, files in os.walk(exp_dir):
            for f in files:
                if f == 'best.pt':
                    best_pt = os.path.join(root, f)
                    break
            if best_pt:
                break
        export_model = YOLO(best_pt) if best_pt else model
        onnx = export_model.export(format='onnx')
        print('[ok] Exported ONNX at', onnx)
    except Exception as ex:
        print('[warn] ONNX export failed:', ex)


if __name__ == '__main__':
    main()

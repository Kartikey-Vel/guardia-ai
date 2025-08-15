from __future__ import annotations
from typing import List, Tuple

import numpy as np

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover
    YOLO = None  # type: ignore

try:
    import onnxruntime as ort  # type: ignore
except Exception:  # pragma: no cover
    ort = None  # type: ignore


# A light wrapper to abstract Ultralytics output
class YoloDetector:
    def __init__(self, weights: str = "yolov8n.pt", conf: float = 0.25, iou: float = 0.45, imgsz: int = 640, device: str = "auto", half: bool = True, extra_weights: List[str] | None = None):
        self.weights = weights
        self.conf = conf
        self.iou = iou
        self.imgsz = imgsz
        self.device = device
        self.half = half
        self.model = None
        self.ort_sess = None
        self.ort_input_name = None
        self.extra_models: List[object] = []
        # Prefer ONNX if weights is .onnx
        if str(self.weights).lower().endswith('.onnx') and ort is not None:
            try:
                # Respect requested device when selecting providers
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if (self.device == 'cuda') else ['CPUExecutionProvider']
                self.ort_sess = ort.InferenceSession(self.weights, providers=providers)
                self.ort_input_name = self.ort_sess.get_inputs()[0].name
            except Exception:
                self.ort_sess = None
        elif YOLO is not None:
            try:
                self.model = YOLO(self.weights)
                if hasattr(self.model, 'to') and self.device and self.device != 'auto':
                    try:
                        self.model.to(self.device)
                    except Exception:
                        pass
            except Exception:
                self.model = None
            # Load extra models if provided
            if extra_weights:
                for w in extra_weights:
                    try:
                        if str(w).lower().endswith('.onnx') and ort is not None:
                            prov = ['CUDAExecutionProvider','CPUExecutionProvider'] if (self.device == 'cuda') else ['CPUExecutionProvider']
                            s = ort.InferenceSession(w, providers=prov)
                            self.extra_models.append(s)
                            continue
                        m = YOLO(w)
                        if hasattr(m, 'to') and self.device and self.device != 'auto':
                            try:
                                m.to(self.device)
                            except Exception:
                                pass
                        self.extra_models.append(m)
                    except Exception:
                        continue

    def available(self) -> bool:
        return (self.model is not None) or (self.ort_sess is not None)

    def detect(self, frame_bgr: np.ndarray) -> List[Tuple[int, int, int, int, str, float]]:
        """Return list of (x1,y1,x2,y2,label,conf) in pixel coords."""
        if not self.available():
            return []
        # ONNX path
        if self.ort_sess is not None:
            return self._detect_onnx(frame_bgr)
        # Ultralytics path
        if self.model is None:
            return []
        predict = getattr(self.model, 'predict', None)
        if predict is None:
            return []
        results = predict(source=frame_bgr, conf=self.conf, iou=self.iou, verbose=False, imgsz=self.imgsz, half=self.half)
        out: List[Tuple[int,int,int,int,str,float]] = []
        if not results:
            return out
        r = results[0]
        names = r.names
        if r.boxes is None:
            return out
        for b in r.boxes:
            xyxy = b.xyxy[0].tolist()
            x1, y1, x2, y2 = map(int, xyxy)
            cls_id = int(b.cls[0].item())
            conf = float(b.conf[0].item())
            label = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
            out.append((x1, y1, x2, y2, label, conf))
        return out

    def _letterbox(self, img: np.ndarray, new_shape: int = 640) -> Tuple[np.ndarray, float, Tuple[int,int]]:
        h, w = img.shape[:2]
        r = min(new_shape / h, new_shape / w)
        new_unpad = (int(round(w * r)), int(round(h * r)))
        dw, dh = new_shape - new_unpad[0], new_shape - new_unpad[1]
        dw //= 2
        dh //= 2
        if (w, h) != new_unpad:
            import cv2
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
        top, bottom = dh, dh
        left, right = dw, dw
        import cv2
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114,114,114))
        return img, r, (dw, dh)

    def _nms(self, dets: List[Tuple[int,int,int,int,int,float]], iou_th: float) -> List[Tuple[int,int,int,int,int,float]]:
        # dets: (x1,y1,x2,y2,cls,conf)
        dets = sorted(dets, key=lambda d: d[-1], reverse=True)
        keep = []
        used = [False]*len(dets)
        def iou(a,b):
            ax1,ay1,ax2,ay2 = a
            bx1,by1,bx2,by2 = b
            inter_x1 = max(ax1,bx1); inter_y1 = max(ay1,by1)
            inter_x2 = min(ax2,bx2); inter_y2 = min(ay2,by2)
            iw = max(0, inter_x2 - inter_x1); ih = max(0, inter_y2 - inter_y1)
            inter = iw*ih
            ua = max(0,(ax2-ax1))*max(0,(ay2-ay1))
            ub = max(0,(bx2-bx1))*max(0,(by2-by1))
            union = ua+ub-inter
            return inter/union if union>0 else 0.0
        for i,a in enumerate(dets):
            if used[i]:
                continue
            used[i]=True
            keep.append(a)
            for j in range(i+1,len(dets)):
                if used[j]:
                    continue
                if a[4]!=dets[j][4]:
                    continue
                if iou(a[:4], dets[j][:4])>=iou_th:
                    used[j]=True
        return keep

    def _ort_to_array(self, out):
        """Best-effort convert ONNXRuntime output to a numpy array."""
        try:
            # Some providers may return sparse tensors with `.values`
            if hasattr(out, 'values'):
                out = out.values
        except Exception:
            pass
        try:
            import numpy as _np  # local import to avoid global stub issues
            if not isinstance(out, _np.ndarray):
                out = _np.array(out)
        except Exception:
            pass
        return out

    def _detect_onnx(self, frame_bgr: np.ndarray) -> List[Tuple[int,int,int,int,str,float]]:
        if self.ort_sess is None or self.ort_input_name is None:
            return []
        img0 = frame_bgr
        img, r, (dw, dh) = self._letterbox(img0, self.imgsz)
        import cv2
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        x = img.astype(np.float32)/255.0
        x = np.transpose(x, (2,0,1))
        x = np.expand_dims(x, 0)
        outs = self.ort_sess.run(None, {self.ort_input_name: x})
        if not outs:
            return []
        out = self._ort_to_array(outs[0])
    # Expect shape (1, N, C); where C >= 6 [x,y,w,h,obj or conf, class scores...]
        preds = out[0] if getattr(out, 'ndim', 0) >= 2 else out
        dets: List[Tuple[int,int,int,int,int,float]] = []
        if preds.ndim != 2 or preds.shape[1] < 6:
            return []
        for row in preds:
            x_c,y_c,w_b,h_b = row[0:4]
            scores = row[5:]
            if scores.size == 0:
                conf = float(row[4])
                cls_id = 0
            else:
                cls_id = int(np.argmax(scores))
                conf = float(scores[cls_id]) * float(row[4])
            if conf < self.conf:
                continue
            # xywh -> xyxy in padded space
            x1 = x_c - w_b/2.0
            y1 = y_c - h_b/2.0
            x2 = x_c + w_b/2.0
            y2 = y_c + h_b/2.0
            # scale back to original image
            # remove padding
            x1 = (x1 - dw)/r; y1 = (y1 - dh)/r; x2 = (x2 - dw)/r; y2 = (y2 - dh)/r
            dets.append((int(max(0,x1)), int(max(0,y1)), int(max(0,x2)), int(max(0,y2)), cls_id, conf))
        dets = self._nms(dets, self.iou)
        # Map class id to string label numerically
        out_boxes: List[Tuple[int,int,int,int,str,float]] = []
        for x1,y1,x2,y2,cls_id,conf in dets:
            out_boxes.append((x1,y1,x2,y2, str(cls_id), float(conf)))
        return out_boxes

    def available_multi(self) -> bool:
        return self.available() or bool(self.extra_models)

    def detect_multi(self, frame_bgr: np.ndarray) -> List[Tuple[int, int, int, int, str, float]]:
        """Run detections across primary and extra models; merge by simple max-conf on identical class and overlapping boxes."""
        boxes = []  # (x1,y1,x2,y2,label,conf)
        if self.available():
            boxes.extend(self.detect(frame_bgr))
        # Collect from extra models
        if YOLO is None and ort is None:
            return boxes
        for m in self.extra_models:
            try:
                # ONNX path (guard access to ort when available)
                if (ort is not None) and isinstance(m, ort.InferenceSession):
                    sess = m
                    input_name = sess.get_inputs()[0].name
                    img0 = frame_bgr
                    img, r, (dw, dh) = self._letterbox(img0, self.imgsz)
                    import cv2
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    x = img.astype(np.float32)/255.0
                    x = np.transpose(x, (2,0,1))
                    x = np.expand_dims(x, 0)
                    outs = sess.run(None, {input_name: x})
                    if not outs:
                        continue
                    out = self._ort_to_array(outs[0])
                    preds = out[0] if getattr(out, 'ndim', 0) >= 2 else out
                    for row in preds:
                        if len(row) < 6:
                            continue
                        x_c,y_c,w_b,h_b = row[0:4]
                        scores = row[5:]
                        if scores.size == 0:
                            conf = float(row[4])
                            cls_id = 0
                        else:
                            cls_id = int(np.argmax(scores))
                            conf = float(scores[cls_id]) * float(row[4])
                        if conf < self.conf:
                            continue
                        x1 = x_c - w_b/2.0; y1 = y_c - h_b/2.0; x2 = x_c + w_b/2.0; y2 = y_c + h_b/2.0
                        x1 = (x1 - dw)/r; y1 = (y1 - dh)/r; x2 = (x2 - dw)/r; y2 = (y2 - dh)/r
                        boxes.append((int(x1), int(y1), int(x2), int(y2), str(cls_id), float(conf)))
                else:
                    predict = getattr(m, 'predict', None)
                    if predict is None:
                        continue
                    results = predict(source=frame_bgr, conf=self.conf, iou=self.iou, verbose=False, imgsz=self.imgsz, half=self.half)
                    if not results:
                        continue
                    r = results[0]
                    names = r.names
                    if r.boxes is None:
                        continue
                    for b in r.boxes:
                        xyxy = b.xyxy[0].tolist()
                        x1, y1, x2, y2 = map(int, xyxy)
                        cls_id = int(b.cls[0].item())
                        conf = float(b.conf[0].item())
                        label = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
                        boxes.append((x1, y1, x2, y2, label, conf))
            except Exception:
                continue
        # Simple NMS by class + IoU threshold: keep max-conf
        def iou(a, b):
            ax1, ay1, ax2, ay2 = a
            bx1, by1, bx2, by2 = b
            inter_x1 = max(ax1, bx1)
            inter_y1 = max(ay1, by1)
            inter_x2 = min(ax2, bx2)
            inter_y2 = min(ay2, by2)
            iw = max(0, inter_x2 - inter_x1)
            ih = max(0, inter_y2 - inter_y1)
            inter = iw * ih
            a_area = max(0, (ax2 - ax1)) * max(0, (ay2 - ay1))
            b_area = max(0, (bx2 - bx1)) * max(0, (by2 - by1))
            union = a_area + b_area - inter
            return inter / union if union > 0 else 0.0
        merged: List[Tuple[int,int,int,int,str,float]] = []
        boxes.sort(key=lambda t: t[-1], reverse=True)
        used = [False] * len(boxes)
        for i, bi in enumerate(boxes):
            if used[i]:
                continue
            used[i] = True
            x1,y1,x2,y2,lab,conf = bi
            for j in range(i+1, len(boxes)):
                if used[j]:
                    continue
                bj = boxes[j]
                if bj[4] != lab:
                    continue
                if iou((x1,y1,x2,y2), bj[:4]) >= 0.5:
                    used[j] = True
            merged.append((x1,y1,x2,y2,lab,conf))
        return merged

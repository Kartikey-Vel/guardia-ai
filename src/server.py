from __future__ import annotations
import os
import time
import threading
import queue
from collections import deque
from typing import Deque, Dict, Any, List, Tuple, Callable
import json

import cv2
import numpy as np
from flask import Flask, Response, render_template_string, jsonify, request
import psutil
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from .config import AppConfig
from .yolo_detector import YoloDetector
from .vision_client import GoogleVisionClient
from .pose_analyzer import PoseAnalyzer
from .utils import FPSLimiter, motion_changed, draw_bbox, draw_label, crop_roi, EventLogger, save_image, name_color_hsv, SimpleTracker, evaluate_hazards, LoiteringMonitor
from .gcp_clients import GCSUploader, PubSubPublisher

# Optional: Gemini summaries
try:
    import google.generativeai as genai
except Exception:
    genai = None

HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Guardia-AI Dashboard</title>
  <style>
    body { font-family: system-ui, Arial, sans-serif; margin: 0; padding: 0; background: #0b0e11; color: #eaecef; }
    header { padding: 12px 16px; background: #11161c; border-bottom: 1px solid #1e232a; }
    .container { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; padding: 16px; }
    .panel { background: #0f141a; border: 1px solid #1e232a; border-radius: 8px; padding: 12px; }
    h2 { margin: 0 0 8px; font-size: 16px; color: #d1d5db; }
    .metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .metric { background: #0b0f14; padding: 8px; border: 1px solid #1a2027; border-radius: 6px; }
    .metric .label { color: #9ca3af; font-size: 12px; }
    .metric .value { font-size: 18px; margin-top: 4px; }
    .events { max-height: 420px; overflow-y: auto; }
    .event { border-bottom: 1px solid #1a2027; padding: 8px 0; }
    code { background: #0b0f14; padding: 2px 4px; border-radius: 4px; }
    img { width: 100%; height: auto; border-radius: 8px; border: 1px solid #1e232a; }
    .summary { white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas; }
    footer { color: #9ca3af; font-size: 12px; text-align: center; margin: 12px 0; }
  </style>
</head>
<body>
  <header><h1>Guardia-AI Dashboard</h1></header>
  <div class="container">
    <div class="panel">
      <h2>Live Stream</h2>
      <img src="/stream" alt="Live video" />
    </div>
    <div class="panel">
      <h2>Metrics</h2>
      <div class="metrics" id="metrics"></div>
    </div>
        <div class="panel" style="grid-column: 1 / span 2;">
      <h2>Recent Events</h2>
      <div class="events" id="events"></div>
    </div>
        <div class="panel" style="grid-column: 1 / span 2;">
            <h2>Zones</h2>
            <div>
                <input id="zx1" type="number" placeholder="x1" style="width:80px"/>
                <input id="zy1" type="number" placeholder="y1" style="width:80px"/>
                <input id="zx2" type="number" placeholder="x2" style="width:80px"/>
                <input id="zy2" type="number" placeholder="y2" style="width:80px"/>
                <button onclick="addZone()">Add Zone</button>
                <button onclick="clearZones()">Clear Zones</button>
            </div>
            <div id="zones"></div>
        </div>
    <div class="panel" style="grid-column: 1 / span 2;">
      <h2>AI Summary</h2>
      <div id="summary" class="summary"></div>
    </div>
  </div>
  <footer>Press 'q' in the local window to stop capture. This dashboard auto-refreshes.</footer>
  <script>
    async function refresh() {
      try {
        const m = await fetch('/api/metrics').then(r => r.json());
        const e = await fetch('/api/events').then(r => r.json());
                const sys = await fetch('/api/system').then(r => r.json());
                const zn = await fetch('/api/zones').then(r => r.json());
        const s = await fetch('/api/summary').then(r => r.json());
        const metrics = document.getElementById('metrics');
        metrics.innerHTML = '';
        Object.entries(m).forEach(([k, v]) => {
          metrics.innerHTML += `<div class="metric"><div class="label">${k}</div><div class="value">${v}</div></div>`;
        });
                metrics.innerHTML += `<div class="metric"><div class="label">CPU %</div><div class="value">${sys.cpu_percent}</div></div>`;
                metrics.innerHTML += `<div class="metric"><div class="label">Mem %</div><div class="value">${sys.mem_percent}</div></div>`;
        const events = document.getElementById('events');
        events.innerHTML = '';
                e.forEach(ev => {
                    const haz = (ev.hazards && ev.hazards.length) ? ` | hazards: ${ev.hazards.join(', ')}` : '';
                    events.innerHTML += `<div class="event"><div><b>${new Date(ev.ts*1000).toLocaleString()}</b></div><div>label: <code>${ev.label}</code> conf: ${ev.confidence?.toFixed(2)}</div><div>harmful: <b>${ev.harmful ? 'YES' : 'NO'}</b>${haz}</div><div>labels: ${ev.allLabels?.join(', ')}</div></div>`;
                });
                const zones = document.getElementById('zones');
                zones.innerHTML = 'Active zones: ' + JSON.stringify(zn);
        document.getElementById('summary').textContent = s.summary || '';
      } catch (err) { /* ignore */ }
      setTimeout(refresh, 1000);
    }
        async function addZone() {
            const zx1 = parseInt(document.getElementById('zx1').value || '0');
            const zy1 = parseInt(document.getElementById('zy1').value || '0');
            const zx2 = parseInt(document.getElementById('zx2').value || '0');
            const zy2 = parseInt(document.getElementById('zy2').value || '0');
            await fetch('/api/zones', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ x1: zx1, y1: zy1, x2: zx2, y2: zy2 }) });
        }
        async function clearZones() {
            await fetch('/api/zones', { method: 'DELETE' });
        }
    refresh();
  </script>
</body>
</html>
"""

class DetectorThread(threading.Thread):
    def __init__(self, cfg: AppConfig, metrics: Dict[str, Any], events: Deque[Dict[str, Any]], event_hook: Callable[[Dict[str, Any]], None] | None = None):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.metrics = metrics
        self.events = events
        self.stop_flag = threading.Event()
        self.frame_lock = threading.Lock()
        self.last_frame: np.ndarray | None = None
        self.event_hook = event_hook

    def run(self) -> None:
        cap = cv2.VideoCapture(self.cfg.source)
        detector = YoloDetector(
            weights=self.cfg.yolo_weights,
            conf=self.cfg.yolo_conf_thresh,
            iou=self.cfg.yolo_iou_thresh,
            imgsz=self.cfg.yolo_imgsz,
            device=self.cfg.device,
            half=self.cfg.half,
        )
        vision = GoogleVisionClient(min_score=self.cfg.vision_min_score) if self.cfg.use_vision else GoogleVisionClient(1.0)
        pose = PoseAnalyzer(self.cfg.pose_min_detection_confidence, self.cfg.pose_min_tracking_confidence) if self.cfg.use_pose else PoseAnalyzer(1, 1)
        vision_limiter = FPSLimiter(self.cfg.max_vision_fps)
        logger = EventLogger(self.cfg.log_dir)

        prev_gray = None
        frame_idx = 0
        tracker = SimpleTracker()
        loiter = LoiteringMonitor(seconds_threshold=self.cfg.loiter_seconds_threshold,
                                  radius_px=self.cfg.loiter_radius_px,
                                  classes=set(self.cfg.loiter_classes))
        t0 = time.time()

        while not self.stop_flag.is_set():
            ok, frame = cap.read()
            if not ok:
                break
            frame_idx += 1
            self.metrics['frames'] = frame_idx

            process_this = True
            if self.cfg.use_motion_filter:
                changed, prev_gray = motion_changed(prev_gray, frame)
                process_this = changed

            if self.cfg.frameskip > 0 and (frame_idx % self.cfg.frameskip != 0):
                process_this = False

            detections: List[Tuple[int, int, int, int, str, float]] = []
            if process_this and detector.available():
                if self.cfg.track_interval <= 1 or frame_idx % self.cfg.track_interval == 0:
                    dets = detector.detect(frame)
                    detections = tracker.update(dets)
                else:
                    detections = tracker.update([])

            harmful_count = 0
            for (x1, y1, x2, y2, label, conf) in detections:
                labels = [label]
                is_person = label.lower() == 'person'
                roi = None
                vlabels: List[Tuple[str, float]] = []

                if self.cfg.use_vision and vision_limiter.allow() and vision.available():
                    roi = crop_roi(frame, (x1, y1, x2, y2))
                    vlabels = vision.label_image(roi)
                    labels.extend([n for n, s in vlabels])

                pose_flags = None
                if self.cfg.use_pose and (is_person or roi is not None) and pose.available():
                    roi_img = roi if roi is not None else frame[max(0, y1):y2, max(0, x1):x2]
                    pose_flags = pose.analyze(roi_img)

                clothing = None
                if is_person:
                    hmid = y1 + (y2 - y1) // 2
                    lower = frame[hmid:y2, x1:x2]
                    clothing = name_color_hsv(lower)

                harmful, hazard_tags = evaluate_hazards(label, vlabels, self.cfg.harmful_labels, self.cfg.advanced_detection)
                if harmful:
                    harmful_count += 1

                color = (0, 0, 255) if harmful else (0, 255, 0)
                draw_bbox(frame, (x1, y1, x2, y2), color=color)
                info = f"{label} {conf:.2f}"
                if self.cfg.use_vision and len(labels) > 1:
                    info += f" | {','.join([l for l in labels if l != label])}"
                if pose_flags and pose_flags.raised_hands:
                    info += " | raised_hands"
                if clothing:
                    info += f" | clothing:{clothing}"
                draw_label(frame, info, x1, y1, color=color)

                if harmful:
                    ts = time.time()
                    ev = {
                        'ts': ts,
                        'box': [int(x1), int(y1), int(x2), int(y2)],
                        'label': label,
                        'allLabels': labels,
                        'confidence': float(conf),
                        'pose': vars(pose_flags) if pose_flags else {},
                        'clothingColor': clothing,
                        'harmful': True,
                        'hazards': hazard_tags,
                    }
                    if self.event_hook:
                        try:
                            self.event_hook(ev)
                        except Exception:
                            pass
                    self.events.appendleft(ev)
                    if len(self.events) > 200:
                        self.events.pop()
                    logger.log(ev)

            # loitering detection based on tracks
            for tid, tr in loiter.check(tracker.get_tracks()):
                bx = tr.get('box', (0, 0, 0, 0))
                x1, y1, x2, y2 = int(bx[0]), int(bx[1]), int(bx[2]), int(bx[3])
                draw_label(frame, "LOITERING", x1, y1 - 8, color=(0, 165, 255))
                draw_bbox(frame, (x1, y1, x2, y2), color=(0, 165, 255))
                ev = {
                    'ts': time.time(),
                    'box': [x1, y1, x2, y2],
                    'label': tr.get('label', 'unknown'),
                    'allLabels': [tr.get('label', 'unknown')],
                    'confidence': float(tr.get('conf', 0.0)),
                    'pose': {},
                    'clothingColor': None,
                    'harmful': False,
                    'hazards': ['loitering'],
                }
                self.events.appendleft(ev)
                if len(self.events) > 200:
                    self.events.pop()
                logger.log(ev)

            # draw hazard zones and check breaches
            for zx1, zy1, zx2, zy2 in self.cfg.hazard_zones:
                cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), (255, 0, 0), 1)
            if self.cfg.hazard_zones:
                zclasses = {c.lower() for c in self.cfg.zone_classes}
                for tid, tr in tracker.get_tracks().items():
                    lbl = str(tr.get('label', '')).lower()
                    if lbl not in zclasses:
                        continue
                    bx = tr.get('box', (0, 0, 0, 0))
                    for zone in self.cfg.hazard_zones:
                        if (bx[0] < zone[2] and bx[2] > zone[0] and bx[1] < zone[3] and bx[3] > zone[1]):
                            ev = {
                                'ts': time.time(),
                                'box': [int(bx[0]), int(bx[1]), int(bx[2]), int(bx[3])],
                                'label': tr.get('label', 'unknown'),
                                'allLabels': [tr.get('label', 'unknown')],
                                'confidence': float(tr.get('conf', 0.0)),
                                'pose': {},
                                'clothingColor': None,
                                'harmful': False,
                                'hazards': ['zone-breach'],
                            }
                            self.events.appendleft(ev)
                            if len(self.events) > 200:
                                self.events.pop()
                            logger.log(ev)
                            break

            # metrics
            dt = time.time() - t0
            self.metrics['fps'] = round(frame_idx / dt, 1) if dt > 0 else 0.0
            self.metrics['harmful_last_frame'] = harmful_count
            self.metrics['last_update'] = int(time.time())

            with self.frame_lock:
                self.last_frame = frame

        cap.release()

    def get_jpeg(self) -> bytes | None:
        with self.frame_lock:
            if self.last_frame is None:
                return None
            ok, jpg = cv2.imencode('.jpg', self.last_frame)
            if not ok:
                return None
            return jpg.tobytes()


def create_app(cfg: AppConfig) -> Flask:
    app = Flask(__name__)

    metrics: Dict[str, Any] = {'fps': 0.0, 'frames': 0, 'harmful_last_frame': 0}
    events: Deque[Dict[str, Any]] = deque(maxlen=200)
    zones_path = os.path.join(cfg.outputs_dir, 'zones.json')
    zones_lock = threading.Lock()
    os.makedirs(cfg.outputs_dir, exist_ok=True)
    # load zones if present
    try:
        if os.path.exists(zones_path):
            with open(zones_path, 'r', encoding='utf-8') as f:
                z = json.load(f)
                if isinstance(z, list):
                    new_zones: List[Tuple[int, int, int, int]] = []
                    for zz in z:
                        if isinstance(zz, (list, tuple)) and len(zz) == 4:
                            x1, y1, x2, y2 = map(int, zz)
                        elif isinstance(zz, dict):
                            x1 = int(zz.get('x1', 0)); y1 = int(zz.get('y1', 0)); x2 = int(zz.get('x2', 0)); y2 = int(zz.get('y2', 0))
                        else:
                            continue
                        new_zones.append((x1, y1, x2, y2))
                    cfg.hazard_zones.clear()
                    cfg.hazard_zones.extend(new_zones)
    except Exception:
        pass

    # Optional: GCS and Pub/Sub clients for mirroring harmful events
    gcs = GCSUploader(cfg.gcs_bucket)
    pub = PubSubPublisher(cfg.pubsub_topic)

    def _mirror_event(ev: Dict[str, Any]) -> None:
        # Publish harmful events and optionally upload snapshot to GCS
        try:
            if not ev.get('harmful'):
                return
            if pub.available():
                pub.publish_json(ev)
            if cfg.use_gcs_upload and gcs.available():
                jpg = det.get_jpeg()
                if jpg:
                    ts = int(ev.get('ts', time.time()))
                    label = str(ev.get('label', 'event')).replace(' ', '_')
                    blob = f"events/{ts}_{label}.jpg"
                    uri = gcs.upload_bytes(jpg, blob, content_type='image/jpeg')
                    if uri:
                        ev.setdefault('artifacts', {})['snapshot_gcs'] = uri
        except Exception:
            pass

    det = DetectorThread(cfg, metrics, events, event_hook=_mirror_event)
    det.start()

    # Gemini client (optional)
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    model = None
    if genai is not None and gemini_api_key:
        try:
            # Lazy import methods to avoid linter complaints when stubs are absent
            getattr(genai, "configure")(api_key=gemini_api_key)
            model = getattr(genai, "GenerativeModel")('gemini-1.5-flash')
        except Exception:
            model = None

    @app.route('/')
    def index():
        return render_template_string(HTML)

    @app.route('/stream')
    def stream():
        def gen():
            while True:
                jpg = det.get_jpeg()
                if jpg is None:
                    time.sleep(0.05)
                    continue
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')
                time.sleep(0.03)
        return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.route('/api/metrics')
    def api_metrics():
        return jsonify(metrics)

    @app.route('/api/events')
    def api_events():
        return jsonify(list(events)[:50])

    @app.route('/api/system')
    def api_system():
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return jsonify({
            'cpu_percent': cpu,
            'mem_total_mb': round(mem.total / (1024*1024), 1),
            'mem_used_mb': round(mem.used / (1024*1024), 1),
            'mem_percent': mem.percent,
            'swap_total_mb': round(swap.total / (1024*1024), 1),
            'swap_used_mb': round(swap.used / (1024*1024), 1),
            'swap_percent': swap.percent,
        })

    @app.route('/api/summary')
    def api_summary():
        if model is None or not events:
            return jsonify({'summary': ''})
        try:
            # summarize last N events
            recent = list(events)[:20]
            text = "\n".join([
                f"{time.strftime('%H:%M:%S', time.localtime(e['ts']))} | harmful={e.get('harmful')} label={e.get('label')} conf={e.get('confidence')} labels={','.join(e.get('allLabels', []))}"
                for e in recent
            ])
            prompt = f"""Summarize the following security detection events into 2-4 bullet points. Focus on harmful items and trends.\n\n{text}\n"""
            resp = model.generate_content(prompt)
            out = resp.text if hasattr(resp, 'text') else ''
            return jsonify({'summary': out})
        except Exception:
            return jsonify({'summary': ''})

    @app.route('/api/zones', methods=['GET', 'POST', 'DELETE'])
    def api_zones():
        def persist():
            try:
                with open(zones_path, 'w', encoding='utf-8') as f:
                    json.dump([
                        {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
                        for (x1, y1, x2, y2) in cfg.hazard_zones
                    ], f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        if request.method == 'GET':
            return jsonify({
                'zones': [
                    {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
                    for (x1, y1, x2, y2) in cfg.hazard_zones
                ],
                'classes': list(cfg.zone_classes),
            })

        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
            try:
                def get_int(field: str) -> int:
                    v = data.get(field, None)
                    if v is None:
                        raise ValueError(f"Missing {field}")
                    return int(v)
                x1 = get_int('x1')
                y1 = get_int('y1')
                x2 = get_int('x2')
                y2 = get_int('y2')
            except (TypeError, ValueError):
                return jsonify({'error': 'x1,y1,x2,y2 must be integers'}), 400
            # Normalize order
            if x1 > x2:
                x1, x2 = x2, x1
            if y1 > y2:
                y1, y2 = y2, y1
            with zones_lock:
                cfg.hazard_zones.append((x1, y1, x2, y2))
                persist()
            return jsonify({'ok': True}), 201

        # DELETE
        with zones_lock:
            cfg.hazard_zones.clear()
            persist()
        return jsonify({'ok': True})

    return app

    # Zones endpoints below (defined after return for readability, but logically placed above). This line won't be reached.


if __name__ == '__main__':
    # basic CLI passthrough for source
    cfg = AppConfig()
    cfg.ensure_dirs()
    app = create_app(cfg)
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=False, threaded=True)

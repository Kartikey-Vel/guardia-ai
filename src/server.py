from __future__ import annotations
import os
import time
import threading
import queue
from collections import deque
from typing import Deque, Dict, Any, List, Tuple, Callable, Optional
import json

import cv2
import numpy as np
from flask import Flask, Response, render_template_string, jsonify, request, make_response
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
from . import environments as envmgr
from . import trusted_store
from .face_auth import FaceAuth
from . import user_store
from . import federated
from .training import JobManager

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
  <title>Guardia-AI</title>
  <style>
    body { font-family: system-ui, Arial, sans-serif; margin: 0; padding: 16px; background: #0b0e11; color: #eaecef; }
    .main { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; max-width: 1200px; margin: 0 auto; }
    .panel { background: #0f141a; border: 1px solid #1e232a; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
    h1 { color: #d1d5db; margin: 0 0 24px 0; text-align: center; }
    h2 { margin: 0 0 12px; font-size: 16px; color: #d1d5db; }
    .auth { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }
    .auth input { padding: 8px; border: 1px solid #1e232a; background: #0b0f14; color: #eaecef; border-radius: 4px; }
    .auth button { padding: 8px 16px; background: #1f2937; border: 1px solid #374151; color: #eaecef; border-radius: 4px; cursor: pointer; }
    .metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .metric { background: #0b0f14; padding: 12px; border: 1px solid #1a2027; border-radius: 6px; text-align: center; }
    .metric .label { color: #9ca3af; font-size: 12px; }
    .metric .value { font-size: 20px; margin-top: 4px; font-weight: bold; }
    .events { max-height: 300px; overflow-y: auto; }
    .event { border-bottom: 1px solid #1a2027; padding: 8px 0; font-size: 14px; }
    .event.harmful { border-left: 3px solid #ef4444; padding-left: 8px; }
    img { width: 100%; height: auto; border-radius: 8px; border: 1px solid #1e232a; }
    .status { color: #9ca3af; font-size: 12px; margin-bottom: 8px; }
    button { padding: 8px 16px; background: #1f2937; border: 1px solid #374151; color: #eaecef; border-radius: 4px; cursor: pointer; margin-right: 8px; }
    button:hover { background: #374151; }
    .hidden { display: none; }
  </style>
</head>
<body>
  <h1>🛡️ Guardia-AI Security System</h1>
  
  <div class="panel">
    <div id="auth_state" class="status">Not logged in</div>
    <div class="auth">
      <input id="auth_user" placeholder="Username"/>
      <input id="auth_pass" type="password" placeholder="Password"/>
      <button onclick="login()">Login</button>
      <button onclick="register()">Register</button>
    </div>
  </div>

  <div class="main">
    <div>
      <div class="panel">
        <h2>📹 Live Stream</h2>
        <img src="/stream" alt="Live video feed" />
      </div>
      
      <div class="panel">
        <h2>📊 Recent Events</h2>
        <div class="events" id="events"></div>
      </div>
    </div>
    
    <div>
      <div class="panel">
        <h2>📈 System Metrics</h2>
        <div class="metrics" id="metrics"></div>
      </div>
      
      <div class="panel" id="simple_controls">
        <h2>⚙️ Quick Setup</h2>
        <div style="margin-bottom: 12px;">
          <input id="purpose" placeholder="Purpose (e.g. home security)" style="width: 100%; padding: 8px; border: 1px solid #1e232a; background: #0b0f14; color: #eaecef; border-radius: 4px;"/>
        </div>
        <button onclick="suggestPersonalized()">Get Personalized Config</button>
        <button onclick="trainPersonalized()">Start Training</button>
        <div id="profile_status" class="status"></div>
        <div id="jobs_list" style="margin-top: 12px; font-size: 13px;"></div>
      </div>
    </div>
  </div>
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
    const envs = await fetch('/api/envs').then(r => r.json());
    const faces = await fetch('/api/face/users').then(r => r.json());
    const trusted = await fetch('/api/face/trusted').then(r => r.json()).catch(() => ({items:[]}));
    const auth = await fetch('/api/auth/state').then(r => r.json());
    const prof = auth.username ? await fetch('/api/profile').then(r => r.json()) : {profile: null};
    const jobs = auth.username ? await fetch('/api/train/jobs').then(r => r.json()) : {jobs: []};
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
                    const trusted = ev.trustedName ? ` | trusted: ${ev.trustedName}` : '';
                    events.innerHTML += `<div class="event"><div><b>${new Date(ev.ts*1000).toLocaleString()}</b></div><div>label: <code>${ev.label}</code> conf: ${ev.confidence?.toFixed(2)}${trusted}</div><div>harmful: <b>${ev.harmful ? 'YES' : 'NO'}</b>${haz}</div><div>labels: ${ev.allLabels?.join(', ')}</div></div>`;
                });
                const zones = document.getElementById('zones');
                zones.innerHTML = 'Active zones: ' + JSON.stringify(zn);
        document.getElementById('summary').textContent = s.summary || '';
        document.getElementById('env_active').innerText = 'Active: ' + (envs.active || '-');
        const envDiv = document.getElementById('env_list');
        envDiv.innerHTML = '';
        (envs.items || []).forEach(n => {
            const b = document.createElement('button');
            b.textContent = 'Select ' + n;
            b.onclick = () => selectEnv(n);
            envDiv.appendChild(b);
            const del = document.createElement('button');
            del.textContent = 'Delete ' + n;
            del.onclick = async () => { await fetch('/api/envs?name=' + encodeURIComponent(n), { method: 'DELETE' }); refresh(); };
            envDiv.appendChild(del);
            envDiv.appendChild(document.createElement('br'));
        });
        document.getElementById('face_enabled').innerText = 'Face Auth: ' + (faces.enabled ? 'enabled' : 'disabled');
        document.getElementById('face_users').innerText = 'Users: ' + JSON.stringify(faces.users || []);
        document.getElementById('face_trusted').innerText = 'Trusted: ' + JSON.stringify(trusted.items || []);
        const slDiv = document.getElementById('face_suppress_labels');
        if (slDiv) {
            slDiv.innerText = 'Suppress labels: ' + JSON.stringify(trusted.suppress_labels || []);
        }
        const slInput = document.getElementById('suppress_labels_input');
        if (slInput && slInput.dataset.init !== '1') {
            slInput.value = (trusted.suppress_labels || []).join(',');
            slInput.dataset.init = '1';
        }
                const authState = document.getElementById('auth_state');
                if (authState) {
                    authState.innerText = auth.username ? ('Logged in as ' + auth.username) : 'Not logged in';
                }
                const profDiv = document.getElementById('profile_status');
                if (profDiv) {
                    if (prof.profile) {
                        profDiv.innerText = 'Purpose: ' + (prof.profile.purpose || '-') + ' | Personalized: ' + (!!prof.profile.personalized);
                    } else {
                        profDiv.innerText = '';
                    }
                }
                const jobsDiv = document.getElementById('jobs_list');
                if (jobsDiv) {
                    jobsDiv.innerHTML = '';
                    (jobs.jobs || []).slice().reverse().forEach(j => {
                        const d = new Date((j.updated_ts||j.created_ts||0)*1000).toLocaleString();
                        const res = j.result ? ' (has result)' : '';
                        const err = j.error ? (' error: ' + j.error) : '';
                        const btn = (j.status==='queued'||j.status==='running') ? `<button onclick="cancelJob('${j.id}')">Cancel</button>` : '';
                        jobsDiv.innerHTML += `<div><b>${j.id}</b> [${j.status}] ${d}${res}${err} ${btn}</div>`;
                    });
                }
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
        async function createEnv() {
            const name = document.getElementById('env_name').value;
            let cfg = {};
            try { cfg = JSON.parse(document.getElementById('env_cfg').value || '{}'); } catch {}
            await fetch('/api/envs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name, config: cfg }) });
            refresh();
        }
        async function deleteEnv() {
            const name = document.getElementById('env_name').value;
            await fetch('/api/envs?name=' + encodeURIComponent(name), { method: 'DELETE' });
            refresh();
        }
        async function selectEnv(name) {
            await fetch('/api/envs/select', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name }) });
            refresh();
        }
        async function suggestEnv() {
            const use_case = document.getElementById('env_usecase').value || 'home security';
            const s = await (await fetch('/api/envs/suggest', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ use_case }) })).json();
            document.getElementById('env_cfg').value = JSON.stringify(s.config || {}, null, 2);
        }
        async function enrollFace() {
            const name = document.getElementById('enroll_name').value;
            const file = document.getElementById('enroll_file').files[0];
            if (!file || !name) return;
            const fd = new FormData();
            fd.append('file', file);
            await fetch('/api/face/enroll/' + encodeURIComponent(name), { method: 'POST', body: fd });
            refresh();
        }
        async function enrollFromStream() {
            const name = document.getElementById('enroll_name').value;
            if (!name) return;
            await fetch('/api/face/enroll-from-frame/' + encodeURIComponent(name), { method: 'POST' });
            refresh();
        }
        async function addTrusted() {
            const name = document.getElementById('trusted_name').value;
            if (!name) return;
            await fetch('/api/face/trusted', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name }) });
            refresh();
        }
        async function cancelJob(id) {
            await fetch('/api/train/jobs/' + encodeURIComponent(id) + '/cancel', { method: 'POST' });
            refresh();
        }
    refresh();
  </script>
</body>
</html>
"""

class DetectorThread(threading.Thread):
    def __init__(self, cfg: AppConfig, metrics: Dict[str, Any], events: Deque[Dict[str, Any]], event_hook: Callable[[Dict[str, Any]], None] | None = None, face_auth=None):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.metrics = metrics
        self.events = events
        self.stop_flag = threading.Event()
        self.frame_lock = threading.Lock()
        self.last_frame: np.ndarray | None = None
        self.event_hook = event_hook
        self.face_auth = face_auth

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
                recognized_name = None
                recognized_matches = 0

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

                    # Optional face recognition on person ROI
                    if self.cfg.use_face_auth and self.face_auth is not None:
                        face_roi = frame[max(0, y1):y2, max(0, x1):x2]
                        rec = self.face_auth.recognize(face_roi)
                        if rec:
                            recognized_name, recognized_matches = rec[0], int(rec[1])

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
                if recognized_name:
                    info += f" | trusted:{recognized_name}"
                draw_label(frame, info, x1, y1, color=color)

                # If a trusted person is recognized, down-weight harmful only for selected labels
                if recognized_name:
                    try:
                        tl = {n.lower() for n in trusted_store.list_trusted()}
                        if recognized_name.lower() in tl:
                            # Suppression list is global or last saved; per-request scoping not available in the detector thread
                            suppress = {l.lower() for l in trusted_store.get_suppress_labels(None)}
                            if label.lower() in suppress:
                                harmful = False
                    except Exception:
                        pass
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
                    if recognized_name:
                        ev['trustedName'] = recognized_name
                    if self.event_hook is not None:
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
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret')
    jobs = JobManager()

    metrics: Dict[str, Any] = {'fps': 0.0, 'frames': 0, 'harmful_last_frame': 0}
    events: Deque[Dict[str, Any]] = deque(maxlen=200)
    def _user_dir(u: str) -> str:
        safe = str(u).strip().lower().replace('/', '_').replace('\\', '_')
        base = os.path.join(cfg.outputs_dir, 'users', safe)
        os.makedirs(base, exist_ok=True)
        return base

    # zones path is per-user; default global path when not logged in
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

    # Shared helpers
    face = FaceAuth(cfg.face_db_dir) if cfg.use_face_auth else None

    det = DetectorThread(cfg, metrics, events, event_hook=_mirror_event, face_auth=face)
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

    # Auth & tokens
    def _b64url(data: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')

    def _b64url_decode(s: str) -> bytes:
        import base64
        pad = '=' * (-len(s) % 4)
        return base64.urlsafe_b64decode(s + pad)

    def _secret_key_bytes() -> bytes:
        sk = app.secret_key or 'dev-secret'
        if isinstance(sk, (bytes, bytearray)):
            return bytes(sk)
        return str(sk).encode('utf-8')

    def sign_token(username: str, ttl_sec: int = 12*3600) -> str:
        import hmac, hashlib, json as _json
        u = username.strip().lower()
        exp = int(time.time()) + ttl_sec
        payload = _b64url(_json.dumps({'u': u, 'exp': exp}).encode('utf-8'))
        sig = hmac.new(_secret_key_bytes(), payload.encode('ascii'), hashlib.sha256).digest()
        return payload + '.' + _b64url(sig)

    def verify_token(token: str) -> Optional[str]:
        import hmac, hashlib, json as _json
        try:
            payload_b64, sig_b64 = token.split('.')
            expected = hmac.new(_secret_key_bytes(), payload_b64.encode('ascii'), hashlib.sha256).digest()
            if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
                return None
            data = _json.loads(_b64url_decode(payload_b64).decode('utf-8'))
            if int(data.get('exp', 0)) < int(time.time()):
                return None
            return str(data.get('u', '')) or None
        except Exception:
            return None

    def current_user() -> Optional[str]:
        # Authorization: Bearer <token> or cookie 'auth'
        authz = request.headers.get('Authorization', '')
        if authz.lower().startswith('bearer '):
            u = verify_token(authz.split(' ', 1)[1].strip())
            if u:
                return u
        tok = request.cookies.get('auth')
        if tok:
            u = verify_token(tok)
            if u:
                return u
        return None

    @app.route('/api/auth/register', methods=['POST'])
    def api_register():
        body = request.get_json(silent=True) or {}
        u = str(body.get('username', '')).strip().lower()
        p = str(body.get('password', ''))
        if not u or not p:
            return jsonify({'ok': False, 'error': 'missing creds'}), 400
        ok = user_store.register_user(u, p)
        if not ok:
            return jsonify({'ok': False, 'error': 'exists'}), 400
        token = sign_token(u)
        resp = make_response(jsonify({'ok': True, 'username': u, 'token': token}))
        resp.set_cookie('auth', token, httponly=True, samesite='Lax')
        return resp

    @app.route('/api/auth/login', methods=['POST'])
    def api_login():
        body = request.get_json(silent=True) or {}
        u = str(body.get('username', '')).strip().lower()
        p = str(body.get('password', ''))
        if not u or not p:
            return jsonify({'ok': False, 'error': 'missing creds'}), 400
        if user_store.authenticate(u, p):
            token = sign_token(u)
            resp = make_response(jsonify({'ok': True, 'username': u, 'token': token}))
            resp.set_cookie('auth', token, httponly=True, samesite='Lax')
            return resp
        return jsonify({'ok': False, 'error': 'invalid creds'}), 401

    @app.route('/api/auth/state')
    def api_auth_state():
        return jsonify({'username': current_user()})

    @app.route('/api/profile', methods=['GET'])
    def api_profile():
        u = current_user()
        if not u:
            return jsonify({'profile': None})
        return jsonify({'profile': user_store.load_profile(u)})

    @app.route('/api/profile/suggest', methods=['POST'])
    def api_profile_suggest():
        body = request.get_json(silent=True) or {}
        purpose = str(body.get('purpose', '')).strip() or 'home security'
        # Use Gemini to produce a suggested config specific to the user's purpose
        if model is not None:
            try:
                prompt = (
                    "Design a JSON config for a personalized security detection environment optimized for '"
                    + purpose +
                    "'. Include: frameskip, yolo_imgsz, track_interval, harmful_labels (list), zone_classes (list), loiter_seconds_threshold, advanced_detection (bool). Keep values practical for a low-resource laptop. Return JSON only."
                )
                resp = model.generate_content(prompt)
                txt = resp.text if hasattr(resp, 'text') else '{}'
                import json as _json
                cfg = _json.loads(txt)
                return jsonify({'purpose': purpose, 'config': cfg})
            except Exception:
                pass
        # Fallback template
        fallback = {
            'frameskip': 2,
            'yolo_imgsz': 480,
            'track_interval': 6,
            'harmful_labels': ['knife','gun','rifle','pistol'],
            'zone_classes': ['person'],
            'loiter_seconds_threshold': 30,
            'advanced_detection': True
        }
        return jsonify({'purpose': purpose, 'config': fallback})

    @app.route('/api/profile/train', methods=['POST'])
    def api_profile_train():
        u = current_user()
        if not u:
            return jsonify({'ok': False, 'error': 'not logged in'}), 401
        # Simulate training/personalization & federated learning coordination
        # In practice: send anonymized gradients to a coordinator; here we just mark personalized
        prof = user_store.load_profile(u)
        prof['personalized'] = True
        # Apply env suggestion if present in the dashboard textarea
        body = request.get_json(silent=True) or {}
        if ('purpose' not in prof or not prof.get('purpose')) and isinstance(body.get('purpose'), str):
            prof['purpose'] = body.get('purpose')
        # Persist suggested config if provided
        if isinstance(body.get('config'), dict):
            prof['config'] = body['config']
        user_store.save_profile(u, prof)
        # Optionally apply the profile to the running detector config
        applied = False
        try:
            cfg_blob = prof.get('config') if isinstance(prof, dict) else None
            if isinstance(cfg_blob, dict):
                cfg.frameskip = int(cfg_blob.get('frameskip', cfg.frameskip))
                cfg.yolo_imgsz = int(cfg_blob.get('yolo_imgsz', cfg.yolo_imgsz))
                cfg.track_interval = int(cfg_blob.get('track_interval', cfg.track_interval))
                if isinstance(cfg_blob.get('harmful_labels'), list):
                    cfg.harmful_labels = set(map(str.lower, cfg_blob['harmful_labels']))
                if isinstance(cfg_blob.get('zone_classes'), list):
                    cfg.zone_classes = list(map(str, cfg_blob['zone_classes']))
                if 'loiter_seconds_threshold' in cfg_blob:
                    cfg.loiter_seconds_threshold = float(cfg_blob['loiter_seconds_threshold'])
                if 'advanced_detection' in cfg_blob:
                    cfg.advanced_detection = bool(cfg_blob['advanced_detection'])
                applied = True
        except Exception:
            applied = False
        # Submit federated update (stub)
        try:
            federated.submit_update(u, prof)
            federated.aggregate()
        except Exception:
            pass
        return jsonify({'ok': True, 'applied': applied})

    # Training job APIs
    @app.route('/api/train/jobs', methods=['GET', 'POST'])
    def api_train_jobs():
        u = current_user()
        if not u:
            return jsonify({'error': 'not logged in'}), 401
        if request.method == 'GET':
            return jsonify({'jobs': jobs.list_for_user(u)})
        body = request.get_json(silent=True) or {}
        purpose = str(body.get('purpose', '')).strip() or None
        cfg_blob = body.get('config', None)
        if cfg_blob is not None and not isinstance(cfg_blob, dict):
            return jsonify({'error': 'config must be object'}), 400
        job = jobs.submit(u, purpose, cfg_blob)
        return jsonify(job), 201

    @app.route('/api/train/jobs/<job_id>', methods=['GET'])
    def api_train_job_get(job_id: str):
        u = current_user()
        if not u:
            return jsonify({'error': 'not logged in'}), 401
        j = jobs.get(u, job_id)
        if not j:
            return jsonify({'error': 'not found'}), 404
        return jsonify(j)

    @app.route('/api/train/jobs/<job_id>/cancel', methods=['POST'])
    def api_train_job_cancel(job_id: str):
        u = current_user()
        if not u:
            return jsonify({'error': 'not logged in'}), 401
        ok = jobs.cancel(u, job_id)
        return jsonify({'ok': ok})

    # Environments API
    @app.route('/api/envs', methods=['GET', 'POST', 'DELETE'])
    def api_envs():
        u = current_user()
        if request.method == 'GET':
            return jsonify({'active': envmgr.get_active(u), 'items': envmgr.list_envs(u)})
        if request.method == 'POST':
            body = request.get_json(silent=True) or {}
            name = str(body.get('name', '')).strip()
            cfg_blob = body.get('config', {})
            if not name:
                return jsonify({'error': 'name required'}), 400
            envmgr.create_env(name, cfg_blob, u)
            return jsonify({'ok': True}), 201
        # DELETE with ?name=
        name = request.args.get('name', '')
        if not name:
            return jsonify({'error': 'name required'}), 400
        ok = envmgr.delete_env(name, u)
        return jsonify({'ok': ok})

    @app.route('/api/envs/select', methods=['POST'])
    def api_envs_select():
        u = current_user()
        body = request.get_json(silent=True) or {}
        name = str(body.get('name', '')).strip()
        if not name:
            return jsonify({'error': 'name required'}), 400
        ok = envmgr.set_active(name, u)
        return jsonify({'ok': ok})

    @app.route('/api/envs/suggest', methods=['POST'])
    def api_envs_suggest():
        body = request.get_json(silent=True) or {}
        use_case = str(body.get('use_case', '')).strip()
        if not use_case:
            return jsonify({'error': 'use_case required'}), 400
        # If Gemini available, ask for a suggested config; else return a heuristic template
        if model is not None:
            try:
                prompt = f"Design a JSON config for a security detection environment optimized for '{use_case}'. Include fields: frameskip, yolo_imgsz, track_interval, harmful_labels (list), zone_classes (list), loiter_seconds_threshold, advanced_detection (bool). Keep it concise. Return JSON only."
                resp = model.generate_content(prompt)
                txt = resp.text if hasattr(resp, 'text') else '{}'
                import json as _json
                cfg = _json.loads(txt)
                return jsonify({'use_case': use_case, 'config': cfg})
            except Exception:
                pass
        # Fallback templates
        templates = {
            'home security': {
                'frameskip': 2, 'yolo_imgsz': 480, 'track_interval': 6,
                'harmful_labels': ['knife','gun','rifle','pistol'],
                'zone_classes': ['person'], 'loiter_seconds_threshold': 30,
                'advanced_detection': True
            },
            'child security': {
                'frameskip': 1, 'yolo_imgsz': 640, 'track_interval': 4,
                'harmful_labels': ['knife','gun'],
                'zone_classes': ['person'], 'loiter_seconds_threshold': 10,
                'advanced_detection': True
            }
        }
        key = use_case.lower()
        cfg = templates.get(key, templates['home security'])
        return jsonify({'use_case': use_case, 'config': cfg})

    # Face auth API
    @app.route('/api/face/users', methods=['GET'])
    def api_face_users():
        if not face:
            return jsonify({'enabled': False, 'users': []})
        return jsonify({'enabled': True, 'users': face.list_users()})

    @app.route('/api/face/users/<name>', methods=['DELETE'])
    def api_face_delete(name: str):
        if not face:
            return jsonify({'enabled': False, 'ok': False})
        ok = face.delete_user(name)
        return jsonify({'ok': ok})

    @app.route('/api/face/enroll/<name>', methods=['POST'])
    def api_face_enroll(name: str):
        if not face:
            return jsonify({'enabled': False, 'ok': False}), 400
        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'file required'}), 400
        file_bytes = file.read()
        img_array = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'error': 'invalid image'}), 400
        ok = face.enroll(name, img)
        return jsonify({'ok': ok})

    @app.route('/api/face/enroll-from-frame/<name>', methods=['POST'])
    def api_face_enroll_from_frame(name: str):
        if not face:
            return jsonify({'enabled': False, 'ok': False}), 400
        jpg = det.get_jpeg()
        if not jpg:
            return jsonify({'error': 'no frame'}), 400
        img_array = np.frombuffer(jpg, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'error': 'decode failed'}), 400
        ok = face.enroll(name, img)
        return jsonify({'ok': ok})

    @app.route('/api/face/trusted', methods=['GET', 'POST', 'DELETE'])
    def api_face_trusted():
        u = current_user()
        if request.method == 'GET':
            return jsonify({'items': trusted_store.list_trusted(u), 'suppress_labels': trusted_store.get_suppress_labels(u)})
        body = request.get_json(silent=True) or {}
        person = str(body.get('name', '')).strip()
        if not person:
            return jsonify({'error': 'name required'}), 400
        if request.method == 'POST':
            try:
                trusted_store.add_trusted(person, u)
            except Exception:
                pass
            return jsonify({'ok': True, 'items': trusted_store.list_trusted(u)})
        # DELETE
        try:
            trusted_store.remove_trusted(person, u)
        except Exception:
            pass
        return jsonify({'ok': True, 'items': trusted_store.list_trusted(u)})

    @app.route('/api/face/trusted/suppress-labels', methods=['GET', 'POST'])
    def api_face_trusted_labels():
        u = current_user()
        if request.method == 'GET':
            return jsonify({'suppress_labels': trusted_store.get_suppress_labels(u)})
        body = request.get_json(silent=True) or {}
        labels = body.get('labels', [])
        if not isinstance(labels, list):
            return jsonify({'error': 'labels must be a list'}), 400
        labels = [str(x).lower() for x in labels]
        try:
            trusted_store.set_suppress_labels(labels, u)
        except Exception:
            pass
        return jsonify({'ok': True, 'suppress_labels': trusted_store.get_suppress_labels(u)})

    

    @app.route('/api/zones', methods=['GET', 'POST', 'DELETE'])
    def api_zones():
        u = current_user()
        def persist():
            try:
                zp = zones_path
                if u:
                    zp = os.path.join(_user_dir(u), 'zones.json')
                with open(zp, 'w', encoding='utf-8') as f:
                    json.dump([
                        {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
                        for (x1, y1, x2, y2) in cfg.hazard_zones
                    ], f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        if request.method == 'GET':
            # Load per-user zones onto cfg.hazard_zones to render consistent view
            try:
                zp = zones_path
                if u:
                    zp = os.path.join(_user_dir(u), 'zones.json')
                if os.path.exists(zp):
                    with open(zp, 'r', encoding='utf-8') as f:
                        z = json.load(f)
                        new_z: List[Tuple[int, int, int, int]] = []
                        for zz in z:
                            x1 = int(zz.get('x1')); y1 = int(zz.get('y1')); x2 = int(zz.get('x2')); y2 = int(zz.get('y2'))
                            new_z.append((x1, y1, x2, y2))
                        with zones_lock:
                            cfg.hazard_zones.clear()
                            cfg.hazard_zones.extend(new_z)
            except Exception:
                pass
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

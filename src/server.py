from __future__ import annotations
import os
import time
import threading
import queue
from collections import deque
from typing import Deque, Dict, Any, List, Tuple, Callable, Optional
import json
from datetime import datetime
import hmac
import hashlib
import base64

import cv2
import numpy as np
from flask import Flask, Response, render_template_string, jsonify, request, make_response, redirect, url_for
import psutil
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    try:
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
    except ImportError:
        # Allow running this file directly: python src/server.py
        import sys as _sys, os as _os
        _sys.path.append(_os.path.dirname(_os.path.dirname(__file__)))
        from src.config import AppConfig
        from src.yolo_detector import YoloDetector
        from src.vision_client import GoogleVisionClient
        from src.pose_analyzer import PoseAnalyzer
        from src.utils import FPSLimiter, motion_changed, draw_bbox, draw_label, crop_roi, EventLogger, save_image, name_color_hsv, SimpleTracker, evaluate_hazards, LoiteringMonitor
        from src.gcp_clients import GCSUploader, PubSubPublisher
        from src import environments as envmgr
        from src import trusted_store
        from src.face_auth import FaceAuth
        from src import user_store
        from src import federated
        from src.training import JobManager
except ImportError:
    # Fallback for running as a script: python src/server.py
    from src.config import AppConfig
    from src.yolo_detector import YoloDetector
    from src.vision_client import GoogleVisionClient
    from src.pose_analyzer import PoseAnalyzer
    from src.utils import FPSLimiter, motion_changed, draw_bbox, draw_label, crop_roi, EventLogger, save_image, name_color_hsv, SimpleTracker, evaluate_hazards, LoiteringMonitor
    from src.gcp_clients import GCSUploader, PubSubPublisher
    from src import environments as envmgr
    from src import trusted_store
    from src.face_auth import FaceAuth
    from src import user_store
    from src import federated
    from src.training import JobManager
# Enhanced system modules
try:
    # Use global singletons/instances where provided
    from .performance_monitor import performance_monitor as perf_mon
    from .cache_manager import (
        detection_cache,
        api_cache,
        image_processor,
        frame_buffer,
        get_cache_stats,
    )
    from .alert_system import (
        alert_manager,
        AlertSeverity,
        AlertType,
        create_threat_alert,
        create_zone_breach_alert,
        create_performance_alert,
    )
    from . import mobile_webapp
    ENHANCED_MODULES_AVAILABLE = True
except ImportError:
    try:
        from src.performance_monitor import performance_monitor as perf_mon
        from src.cache_manager import (
            detection_cache,
            api_cache,
            image_processor,
            frame_buffer,
            get_cache_stats,
        )
        from src.alert_system import (
            alert_manager,
            AlertSeverity,
            AlertType,
            create_threat_alert,
            create_zone_breach_alert,
            create_performance_alert,
        )
        from src import mobile_webapp
        ENHANCED_MODULES_AVAILABLE = True
    except ImportError:
        ENHANCED_MODULES_AVAILABLE = False
        perf_mon = None
        detection_cache = None
        api_cache = None
        image_processor = None
        frame_buffer = None
        def get_cache_stats():
            return {}
        alert_manager = None
        class _DummySeverity:
            def __init__(self, *_args, **_kwargs):
                pass
        class _DummyType(_DummySeverity):
            pass
        AlertSeverity = _DummySeverity  # type: ignore
        AlertType = _DummyType  # type: ignore

# Optional: Gemini summaries
try:
    import google.generativeai as genai
except Exception:
    genai = None

LOGIN_HTML = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Login - Guardia-AI</title>
    <style>
        body { font-family: system-ui, Arial, sans-serif; background: #0b0e11; color: #eaecef; display:flex; align-items:center; justify-content:center; height:100vh; }
        .card { background:#0f141a; border:1px solid #1e232a; padding:24px; border-radius:8px; width: 320px; }
        h1 { font-size:18px; margin:0 0 16px; }
        input { width:100%; padding:10px; margin:8px 0; border:1px solid #1e232a; background:#0b0f14; color:#eaecef; border-radius:6px; }
        button { width:100%; padding:10px; margin-top:8px; background:#1f2937; border:1px solid #374151; color:#eaecef; border-radius:6px; cursor:pointer; }
        .alt { text-align:center; font-size:12px; color:#9ca3af; margin-top:8px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🛡️ Guardia-AI Login</h1>
        <input id="username" placeholder="Username"/>
        <input id="password" type="password" placeholder="Password"/>
        <button onclick="login()">Login</button>
        <button onclick="register()">Register</button>
        <div id="msg" class="alt"></div>
    </div>
    <script>
        async function login() {
            const body = { username: document.getElementById('username').value, password: document.getElementById('password').value };
            const r = await fetch('/api/auth/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
            const j = await r.json();
            document.getElementById('msg').innerText = j.ok ? 'Logged in' : (j.error||'Error');
            if (j.ok) location.href = '/';
        }
        async function register() {
            const body = { username: document.getElementById('username').value, password: document.getElementById('password').value };
            const r = await fetch('/api/auth/register', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
            const j = await r.json();
            document.getElementById('msg').innerText = j.ok ? 'Registered' : (j.error||'Error');
            if (j.ok) location.href = '/';
        }
    </script>
</body>
</html>
"""

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
        /* Onboarding overlay */
        .overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: none; align-items: center; justify-content: center; z-index: 1000; }
        .wizard { background: #0f141a; border: 1px solid #1e232a; border-radius: 8px; width: 520px; max-width: 95vw; padding: 20px; }
        .wizard h2 { margin: 0 0 12px; }
        .wizard .actions { display: flex; gap: 8px; margin-top: 12px; }
  </style>
</head>
<body>
  <h1>🛡️ Guardia-AI Security System</h1>

    <!-- Onboarding Overlay -->
    <div id="onboard_overlay" class="overlay">
        <div class="wizard">
            <h2>Welcome! Let’s set up your experience</h2>
            <div id="wiz_step1">
                <p>Would you like to enable face recognition for personalized alerts and trusted-person detection?</p>
                <div class="actions">
                    <button onclick="onFaceIntent('enroll')">Yes, set it up</button>
                    <button onclick="onFaceIntent('later')">Not now</button>
                    <button onclick="onFaceIntent('declined')">No thanks</button>
                </div>
            </div>
            <div id="wiz_step2" class="hidden">
                <p>Enroll your face now. You can upload a photo or capture from the live stream.</p>
                <input id="wiz_file" type="file" accept="image/*" />
                <div class="actions">
                    <button onclick="wizUpload()">Upload photo</button>
                    <button onclick="wizCapture()">Capture from stream</button>
                    <button onclick="wizSkipLater()">Skip for now</button>
                </div>
                <div id="wiz_msg" class="status"></div>
            </div>
            <div id="wiz_done" class="hidden">
                <p>All set! You can add faces later from the dashboard.</p>
                <div class="actions">
                    <button onclick="closeWizard()">Go to dashboard</button>
                </div>
            </div>
        </div>
    </div>
  
  <div class="panel">
    <div id="auth_state" class="status">Not logged in</div>
    <div class="auth">
      <input id="auth_user" placeholder="Username"/>
      <input id="auth_pass" type="password" placeholder="Password"/>
      <button onclick="login()">Login</button>
      <button onclick="register()">Register</button>
    <button onclick="logout()">Logout</button>
    <button onclick="resumeOnboarding()">Resume onboarding</button>
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

            <div class="panel">
                <h2>🚨 Alerts</h2>
                <div id="alerts_stats" class="status">No data</div>
                <div id="alerts_list" class="events"></div>
                <div style="margin-top:8px;">
                    <button onclick="testAlert()">Send Test Notification</button>
                </div>
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

            <div class="panel">
                <h2>🧠 Performance</h2>
                <div id="perf_summary" class="status">No performance data</div>
                <div id="perf_current" class="metrics" style="margin-top:8px;"></div>
            </div>

            <div class="panel">
                <h2>🔧 Capture Diagnostics</h2>
                <div class="metrics" id="capture_diag"></div>
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
                // Check auth first; if not logged in, skip other calls to avoid 401 spam
                const auth = await fetch('/api/auth/state').then(r => r.json());
                const authState = document.getElementById('auth_state');
                if (authState) {
                    authState.innerText = auth.username ? ('Logged in as ' + auth.username) : 'Not logged in';
                }
                if (!auth.username) {
                    setTimeout(refresh, 1000);
                    return;
                }

    // Onboarding state
    const onboard = await fetch('/api/onboarding/state').then(r => r.json());
    handleOnboarding(onboard);

                const m = await fetch('/api/metrics').then(r => r.json());
                const e = await fetch('/api/events').then(r => r.json());
                const sys = await fetch('/api/system').then(r => r.json());
                const zn = await fetch('/api/zones').then(r => r.json());
                const s = await fetch('/api/summary').then(r => r.json());
                const perf = await fetch('/api/performance').then(r => r.ok ? r.json() : null).catch(()=>null);
                const alerts = await fetch('/api/alerts').then(r => r.ok ? r.json() : {alerts:[], stats:{}}).catch(()=>({alerts:[], stats:{}}));
                const envs = await fetch('/api/envs').then(r => r.json());
                const faces = await fetch('/api/face/users').then(r => r.json());
                const trusted = await fetch('/api/face/trusted').then(r => r.json()).catch(() => ({items:[]}));
                const prof = await fetch('/api/profile').then(r => r.json());
                const jobs = await fetch('/api/train/jobs').then(r => r.json());
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
                // authState updated above
                const profDiv = document.getElementById('profile_status');
                if (profDiv) {
                    if (prof && prof.profile) {
                        profDiv.innerText = 'Purpose: ' + (prof.profile.purpose || '-') + ' | Personalized: ' + (!!prof.profile.personalized);
                    } else {
                        profDiv.innerText = '';
                    }
                }
                const jobsDiv = document.getElementById('jobs_list');
                if (jobsDiv) {
                    jobsDiv.innerHTML = '';
                    ((jobs && jobs.jobs) || []).slice().reverse().forEach(j => {
                        const d = new Date((j.updated_ts||j.created_ts||0)*1000).toLocaleString();
                        const res = j.result ? ' (has result)' : '';
                        const err = j.error ? (' error: ' + j.error) : '';
                        const btn = (j.status==='queued'||j.status==='running') ? `<button onclick="cancelJob('${j.id}')">Cancel</button>` : '';
                        jobsDiv.innerHTML += `<div><b>${j.id}</b> [${j.status}] ${d}${res}${err} ${btn}</div>`;
                    });
                }

                // Performance summary
                const perfDiv = document.getElementById('perf_summary');
                const perfCur = document.getElementById('perf_current');
                if (perfDiv) {
                    if (!perf || !perf.summary) {
                        perfDiv.innerText = 'Performance monitor not available';
                    } else {
                        const s = perf.summary || {};
                        const a = perf.adaptive_settings || {};
                        perfDiv.innerText = `avg cpu ${s.avg_cpu_percent}% | avg mem ${s.avg_memory_percent}% | avg fps ${s.avg_fps} | avg inf ${s.avg_inference_time_ms}ms | samples ${s.samples_collected}`;
                        perfCur.innerHTML = '';
                        const cm = perf.current_metrics || {};
                        Object.entries(cm).forEach(([k, v]) => {
                            perfCur.innerHTML += `<div class="metric"><div class="label">${k}</div><div class="value">${v}</div></div>`;
                        });
                    }
                }

                // Alerts
                const aStats = document.getElementById('alerts_stats');
                const aList = document.getElementById('alerts_list');
                if (aStats && aList) {
                    const st = alerts.stats || {};
                    aStats.innerText = `total: ${st.total||0} | unack: ${st.unacknowledged||0} | by severity: ${JSON.stringify(st.by_severity||{})}`;
                    aList.innerHTML = '';
                    (alerts.alerts||[]).forEach(al => {
                        const ts = new Date((al.timestamp||al.created_ts||0)*1000).toLocaleString();
                        const sev = al.severity || al.level || 'UNKNOWN';
                        const id = al.id || al.alert_id || '';
                        const acked = !!al.acknowledged;
                        const btn = acked ? '' : `<button onclick=\"ackAlert('${id}')\">Acknowledge</button>`;
                        aList.innerHTML += `<div class="event ${sev.toLowerCase()}"><div><b>${ts}</b> [${sev}] ${al.type||al.kind||'ALERT'}</div><div>${al.title||al.message||'-'}</div><div>${al.description||''}</div><div>id: <code>${id}</code> ${acked?'(ack)':''} ${btn}</div></div>`;
                    });
                }

                // Capture diagnostics from metrics
                const capDiv = document.getElementById('capture_diag');
                if (capDiv) {
                    const diagKeys = ['capture_backend','capture_source','frame_width','frame_height','fps','frames','frames_skipped','frame_skip_ratio','read_failures','last_error'];
                    capDiv.innerHTML = '';
                    diagKeys.forEach(k => {
                        if (m[k] !== undefined) {
                            capDiv.innerHTML += `<div class="metric"><div class="label">${k}</div><div class="value">${m[k]}</div></div>`;
                        }
                    });
                }
      } catch (err) { /* ignore */ }
      setTimeout(refresh, 1000);
    }

        function handleOnboarding(ob) {
            const ov = document.getElementById('onboard_overlay');
            const s1 = document.getElementById('wiz_step1');
            const s2 = document.getElementById('wiz_step2');
            const sd = document.getElementById('wiz_done');
            if (!ov || !ob) return;
            if (ob.done) {
                ov.style.display = 'none';
                return;
            }
            ov.style.display = 'flex';
            const intent = ob.steps?.face_intent || 'unknown';
            const enrolled = !!ob.steps?.face_enrolled;
            s1.classList.toggle('hidden', intent !== 'unknown');
            s2.classList.toggle('hidden', !(intent === 'enroll' && !enrolled));
            sd.classList.toggle('hidden', !(intent !== 'enroll' || enrolled));
        }

        async function onFaceIntent(choice) {
            await fetch('/api/onboarding/face/intent', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ choice }) });
            // If declined, complete immediately
            if (choice === 'declined' || choice === 'later') {
                await fetch('/api/onboarding/complete', { method:'POST' });
            }
        }
        async function wizUpload() {
            const f = document.getElementById('wiz_file').files[0];
            if (!f) { document.getElementById('wiz_msg').innerText = 'Pick a photo first'; return; }
            const fd = new FormData(); fd.append('file', f);
            const r = await fetch('/api/onboarding/face/enroll-upload', { method:'POST', body: fd });
            const j = await r.json().catch(()=>({ok:false}));
            document.getElementById('wiz_msg').innerText = j.ok ? 'Enrolled' : (j.error||'Failed');
            if (j.ok) await fetch('/api/onboarding/complete', { method:'POST' });
        }
        async function wizCapture() {
            const r = await fetch('/api/onboarding/face/enroll-from-frame', { method:'POST' });
            const j = await r.json().catch(()=>({ok:false}));
            document.getElementById('wiz_msg').innerText = j.ok ? 'Enrolled from stream' : (j.error||'Failed');
            if (j.ok) await fetch('/api/onboarding/complete', { method:'POST' });
        }
        async function wizSkipLater() {
            await onFaceIntent('later');
        }
        function closeWizard() {
            document.getElementById('onboard_overlay').style.display = 'none';
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
        async function ackAlert(id) {
            if (!id) return;
            await fetch('/api/alerts/acknowledge', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ alert_id: id }) });
            refresh();
        }
        async function testAlert() {
            await fetch('/api/alerts/test', { method:'POST' }).catch(()=>{});
        }
        async function login() {
            const body = { username: document.getElementById('auth_user').value, password: document.getElementById('auth_pass').value };
            await fetch('/api/auth/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
            setTimeout(refresh, 100);
        }
        async function register() {
            const body = { username: document.getElementById('auth_user').value, password: document.getElementById('auth_pass').value };
            await fetch('/api/auth/register', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
            setTimeout(refresh, 100);
        }
        async function logout() {
            await fetch('/api/auth/logout', { method:'POST' });
            location.reload();
        }
        async function resumeOnboarding() {
            const ob = await fetch('/api/onboarding/state').then(r => r.json()).catch(()=>null);
            if (ob) { handleOnboarding(ob); }
        }
    refresh();
  </script>
</body>
</html>
"""

class DetectorThread(threading.Thread):
    def __init__(self, cfg: AppConfig, metrics: Dict[str, Any], events: Deque[Dict[str, Any]], event_hook: Callable[[Dict[str, Any]], None] | None = None, face_auth=None, perf=None, dcache=None):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.metrics = metrics
        self.events = events
        self.stop_flag = threading.Event()
        self.frame_lock = threading.Lock()
        # last processed frame buffer
        self.last_frame = None
        # hooks and collaborators
        self.event_hook = event_hook
        self.face_auth = face_auth
        self.perf = perf
        self.dcache = dcache
        # capture diagnostics
        self.capture_backend = None
        self.read_failures = 0
        self.last_error = None

    def _open_capture(self):
        src = self.cfg.source
        try:
            # Prefer DirectShow on Windows for webcams
            if isinstance(src, int) or (isinstance(src, str) and src.isdigit()):
                cam_idx = int(src)
                cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
                self.capture_backend = 'CAP_DSHOW'
            else:
                # Try default backend
                cap = cv2.VideoCapture(src)
                self.capture_backend = 'DEFAULT'
                # Fallback to FFMPEG for network streams
                if not cap.isOpened() and str(src).lower().startswith(("rtsp://", "http://", "https://")):
                    cap.release()
                    cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
                    self.capture_backend = 'CAP_FFMPEG'
        except Exception:
            cap = cv2.VideoCapture(self.cfg.source)
            self.capture_backend = 'DEFAULT'
        return cap

    def run(self) -> None:
        cap = self._open_capture()
        if not cap or not cap.isOpened():
            print("[Guardia] ERROR: Unable to open video source:", self.cfg.source)
            # Small retry loop before giving up
            for i in range(3):
                time.sleep(1.0)
                cap = self._open_capture()
                if cap and cap.isOpened():
                    break
            if not cap or not cap.isOpened():
                print("[Guardia] FATAL: Video source cannot be opened. Exiting detector thread.")
                self.last_error = 'open_failed'
                return
        detector = YoloDetector(
            weights=self.cfg.yolo_weights,
            conf=self.cfg.yolo_conf_thresh,
            iou=self.cfg.yolo_iou_thresh,
            imgsz=self.cfg.yolo_imgsz,
            device=self.cfg.device,
            half=self.cfg.half,
            extra_weights=self.cfg.yolo_extra_weights,
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
        
        # Performance monitoring integration (placeholders for future enhancement)
        fps_counter = 0
        fps_timer = time.time()
        frames_skipped = 0

        while not self.stop_flag.is_set():
            frame_start_time = time.time()
            
            ok, frame = cap.read()
            if not ok:
                self.read_failures += 1
                self.last_error = 'read_failed'
                time.sleep(0.05)
                continue
            frame_idx += 1
            fps_counter += 1
            self.metrics['frames'] = frame_idx

            process_this = True
            skip_reason = None
            
            if self.cfg.use_motion_filter:
                changed, prev_gray = motion_changed(prev_gray, frame)
                if not changed:
                    process_this = False
                    skip_reason = "no_motion"

            if self.cfg.frameskip > 0 and (frame_idx % self.cfg.frameskip != 0):
                process_this = False
                skip_reason = "frameskip"
                frames_skipped += 1

            detections: List[Tuple[int, int, int, int, str, float]] = []
            inference_start = time.time()
            detection_count = 0
            
            if process_this and detector.available():
                if self.cfg.track_interval <= 1 or frame_idx % self.cfg.track_interval == 0:
                    # Attempt cache
                    dets_cached = None
                    if ENHANCED_MODULES_AVAILABLE and self.dcache is not None:
                        try:
                            dets_cached = self.dcache.get_detection(frame)
                        except Exception:
                            dets_cached = None
                    if dets_cached is not None:
                        dets = dets_cached
                    else:
                        # if extra models exist, use merged detection
                        if detector.available_multi():
                            dets = detector.detect_multi(frame)
                        else:
                            dets = detector.detect(frame)
                        if ENHANCED_MODULES_AVAILABLE and self.dcache is not None:
                            try:
                                self.dcache.cache_detection(frame, dets)
                            except Exception:
                                pass
                    detections = tracker.update(dets)
                else:
                    detections = tracker.update([])
                
                detection_count = len(detections)
            
            inference_time = (time.time() - inference_start) * 1000

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
                    if ENHANCED_MODULES_AVAILABLE and (alert_manager is not None):
                        try:
                            sev_hi = getattr(AlertSeverity, 'CRITICAL', None)
                            sev_hi2 = getattr(AlertSeverity, 'HIGH', None)
                            t_threat = getattr(AlertType, 'THREAT_DETECTED', None)
                            if sev_hi and sev_hi2 and t_threat:
                                sev = sev_hi if any(h in ('gun','rifle','pistol') for h in [label.lower(), *[l.lower() for l in labels]]) else sev_hi2
                                alert_manager.create_alert(t_threat, sev, f"Harmful object detected: {label}", f"Detected {label} with conf {conf:.2f}", data=ev)
                        except Exception:
                            pass

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
                if ENHANCED_MODULES_AVAILABLE and (alert_manager is not None):
                    try:
                        sev_med = getattr(AlertSeverity, 'MEDIUM', None)
                        t_loit = getattr(AlertType, 'LOITERING', None)
                        if sev_med and t_loit:
                            alert_manager.create_alert(t_loit, sev_med, "Loitering detected", "An individual has been detected loitering.", data=ev)
                    except Exception:
                        pass

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
                            if ENHANCED_MODULES_AVAILABLE and (alert_manager is not None):
                                try:
                                    sev_med = getattr(AlertSeverity, 'MEDIUM', None)
                                    t_zb = getattr(AlertType, 'ZONE_BREACH', None)
                                    if sev_med and t_zb:
                                        alert_manager.create_alert(t_zb, sev_med, "Zone breach detected", "Object entered restricted zone.", data=ev)
                                except Exception:
                                    pass
                            break

            # Calculate performance metrics
            frame_processing_time = (time.time() - frame_start_time) * 1000
            frame_skip_ratio = frames_skipped / max(1, frame_idx)
            
            # Update FPS calculation
            if time.time() - fps_timer >= 1.0:
                actual_fps = fps_counter / (time.time() - fps_timer)
                fps_counter = 0
                fps_timer = time.time()

            # metrics
            dt = time.time() - t0
            current_fps = round(frame_idx / dt, 1) if dt > 0 else 0.0
            self.metrics['fps'] = current_fps
            self.metrics['harmful_last_frame'] = harmful_count
            self.metrics['last_update'] = int(time.time())
            # capture diagnostics in metrics
            try:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                self.metrics['frame_width'] = w
                self.metrics['frame_height'] = h
            except Exception:
                pass
            self.metrics['capture_backend'] = (self.capture_backend or 'unknown')
            self.metrics['capture_source'] = str(self.cfg.source)
            self.metrics['frames_skipped'] = frames_skipped
            self.metrics['frame_skip_ratio'] = frame_skip_ratio
            self.metrics['read_failures'] = self.read_failures
            if self.last_error:
                self.metrics['last_error'] = self.last_error

            # Record performance metrics
            if ENHANCED_MODULES_AVAILABLE and self.perf is not None:
                try:
                    self.perf.record_metrics(
                        fps=current_fps,
                        inference_time_ms=inference_time,
                        frame_processing_time_ms=frame_processing_time,
                        detection_count=detection_count,
                        frame_skip_ratio=frame_skip_ratio,
                    )
                except Exception:
                    pass

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
                jpg = det.get_jpeg() if det is not None else None
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

    det: DetectorThread | None = None
    det_lock = threading.Lock()
    def ensure_detector_started():
        nonlocal det
        with det_lock:
            if det is None:
                d = DetectorThread(
                    cfg, metrics, events,
                    event_hook=_mirror_event,
                    face_auth=face,
                    perf=(perf_mon if ENHANCED_MODULES_AVAILABLE else None),
                    dcache=(detection_cache if ENHANCED_MODULES_AVAILABLE else None),
                )
                d.start()
                det = d

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

    # Auth & tokens (moved early so routes below can reference current_user())
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

    @app.route('/login')
    def login_page():
        # If already logged in, go home
        if cfg.require_auth and current_user():
            return redirect('/')
        return render_template_string(LOGIN_HTML)

    @app.route('/')
    def index():
        if cfg.require_auth and not current_user():
            return redirect(url_for('login_page'))
        ensure_detector_started()
        return render_template_string(HTML)

    @app.route('/stream')
    def stream():
        if cfg.require_auth and not current_user():
            return redirect(url_for('login_page'))
        ensure_detector_started()
        dref = det  # after ensure, det should be non-None
        def gen():
            while True:
                jpg = dref.get_jpeg() if (dref is not None) else None
                if jpg is None:
                    time.sleep(0.05)
                    continue
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')
                time.sleep(0.03)
        return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.route('/api/metrics')
    def api_metrics():
        if cfg.require_auth and not current_user():
            return jsonify({'error':'unauthorized'}), 401
        u = current_user()
        if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
            cached = api_cache.get_response('/api/metrics', user=u)
            if cached is not None:
                return jsonify(cached)
        data = dict(metrics)
        if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
            api_cache.cache_response('/api/metrics', data, user=u)
        return jsonify(data)

    @app.route('/api/events')
    def api_events():
        if cfg.require_auth and not current_user():
            return jsonify({'error':'unauthorized'}), 401
        u = current_user()
        if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
            cached = api_cache.get_response('/api/events', user=u)
            if cached is not None:
                return jsonify(cached)
        data = list(events)[:50]
        if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
            api_cache.cache_response('/api/events', data, user=u)
        return jsonify(data)

    @app.route('/api/system')
    def api_system():
        if cfg.require_auth and not current_user():
            return jsonify({'error':'unauthorized'}), 401
        u = current_user()
        if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
            cached = api_cache.get_response('/api/system', user=u)
            if cached is not None:
                return jsonify(cached)
        cpu = psutil.cpu_percent(interval=0.0)
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        data = {
            'cpu_percent': cpu,
            'mem_total_mb': round(mem.total / (1024*1024), 1),
            'mem_used_mb': round(mem.used / (1024*1024), 1),
            'mem_percent': mem.percent,
            'swap_total_mb': round(swap.total / (1024*1024), 1),
            'swap_used_mb': round(swap.used / (1024*1024), 1),
            'swap_percent': swap.percent,
        }
        if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
            api_cache.cache_response('/api/system', data, user=u)
        return jsonify(data)

    @app.route('/api/summary')
    def api_summary():
        if cfg.require_auth and not current_user():
            return jsonify({'summary': ''})
        u = current_user()
        if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
            cached = api_cache.get_response('/api/summary', user=u)
            if cached is not None:
                return jsonify(cached)
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
            data = {'summary': out}
            if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
                api_cache.cache_response('/api/summary', data, user=u)
            return jsonify(data)
        except Exception:
            return jsonify({'summary': ''})

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

    @app.route('/api/auth/logout', methods=['POST'])
    def api_logout():
        resp = make_response(jsonify({'ok': True}))
        resp.delete_cookie('auth')
        return resp

    # Onboarding APIs
    def _onboard_get(u: str) -> Dict[str, Any]:
        prof = user_store.load_profile(u)
        ob = prof.get('onboarding') if isinstance(prof, dict) else None
        if not isinstance(ob, dict):
            ob = {'steps': {'face_intent': 'unknown', 'face_enrolled': False}, 'done': False}
        return ob

    def _onboard_save(u: str, ob: Dict[str, Any]) -> None:
        prof = user_store.load_profile(u)
        if not isinstance(prof, dict):
            prof = {}
        prof['onboarding'] = ob
        user_store.save_profile(u, prof)

    @app.route('/api/onboarding/state')
    def api_onboarding_state():
        u = current_user()
        if not u:
            return jsonify({'done': False, 'steps': {'face_intent': 'unknown', 'face_enrolled': False}})
        return jsonify(_onboard_get(u))

    @app.route('/api/onboarding/face/intent', methods=['POST'])
    def api_onboarding_face_intent():
        u = current_user()
        if not u:
            return jsonify({'ok': False, 'error': 'not logged in'}), 401
        body = request.get_json(silent=True) or {}
        choice = str(body.get('choice','unknown')).strip().lower()
        if choice not in ('enroll','later','declined'):
            return jsonify({'ok': False, 'error': 'invalid choice'}), 400
        ob = _onboard_get(u)
        ob['steps']['face_intent'] = choice
        # If declined, mark done right away
        if choice in ('later','declined'):
            ob['done'] = True
        _onboard_save(u, ob)
        return jsonify({'ok': True, 'state': ob})

    @app.route('/api/onboarding/face/enroll-upload', methods=['POST'])
    def api_onboarding_face_enroll_upload():
        u = current_user()
        if not u:
            return jsonify({'ok': False, 'error': 'not logged in'}), 401
        if not face:
            return jsonify({'ok': False, 'error': 'face auth disabled'}), 400
        file = request.files.get('file')
        if not file:
            return jsonify({'ok': False, 'error': 'file required'}), 400
        img_array = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'ok': False, 'error': 'decode failed'}), 400
        ok = face.enroll(u, img)
        ob = _onboard_get(u)
        if ok:
            ob['steps']['face_enrolled'] = True
        _onboard_save(u, ob)
        return jsonify({'ok': ok, 'state': ob})

    @app.route('/api/onboarding/face/enroll-from-frame', methods=['POST'])
    def api_onboarding_face_enroll_from_frame():
        u = current_user()
        if not u:
            return jsonify({'ok': False, 'error': 'not logged in'}), 401
        if not face:
            return jsonify({'ok': False, 'error': 'face auth disabled'}), 400
        ensure_detector_started()
        jpg = det.get_jpeg() if det else None
        if not jpg:
            return jsonify({'ok': False, 'error': 'no frame'}), 400
        img_array = np.frombuffer(jpg, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'ok': False, 'error': 'decode failed'}), 400
        ok = face.enroll(u, img)
        ob = _onboard_get(u)
        if ok:
            ob['steps']['face_enrolled'] = True
        _onboard_save(u, ob)
        return jsonify({'ok': ok, 'state': ob})

    @app.route('/api/onboarding/complete', methods=['POST'])
    def api_onboarding_complete():
        u = current_user()
        if not u:
            return jsonify({'ok': False, 'error': 'not logged in'}), 401
        ob = _onboard_get(u)
        ob['done'] = True
        _onboard_save(u, ob)
        return jsonify({'ok': True, 'state': ob})

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
        if cfg.require_auth and not u:
            return jsonify({'error': 'not logged in'}), 401
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
        if cfg.require_auth and not current_user():
            return jsonify({'enabled': False, 'users': []}), 401
        if not face:
            return jsonify({'enabled': False, 'users': []})
        return jsonify({'enabled': True, 'users': face.list_users()})

    @app.route('/api/face/users/<name>', methods=['DELETE'])
    def api_face_delete(name: str):
        if cfg.require_auth and not current_user():
            return jsonify({'enabled': False, 'ok': False}), 401
        if not face:
            return jsonify({'enabled': False, 'ok': False})
        ok = face.delete_user(name)
        return jsonify({'ok': ok})

    @app.route('/api/face/enroll/<name>', methods=['POST'])
    def api_face_enroll(name: str):
        if cfg.require_auth and not current_user():
            return jsonify({'enabled': False, 'ok': False}), 401
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
        if cfg.require_auth and not current_user():
            return jsonify({'enabled': False, 'ok': False}), 401
        if not face:
            return jsonify({'enabled': False, 'ok': False}), 400
        ensure_detector_started()
        jpg = det.get_jpeg() if det else None
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
        if cfg.require_auth and not u:
            return jsonify({'error': 'not logged in'}), 401
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
        if cfg.require_auth and not u:
            return jsonify({'error': 'not logged in'}), 401
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
        if cfg.require_auth and not u:
            return jsonify({'error': 'not logged in'}), 401
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

    # Performance monitoring endpoints
    @app.route('/api/performance')
    def api_performance():
        if cfg.require_auth and not current_user():
            return jsonify({'error':'unauthorized'}), 401
        if not ENHANCED_MODULES_AVAILABLE or perf_mon is None:
            return jsonify({'error': 'performance module not available'}), 503
        return jsonify(perf_mon.get_performance_summary())

    @app.route('/api/cache-stats')
    def api_cache_stats():
        if cfg.require_auth and not current_user():
            return jsonify({'error':'unauthorized'}), 401
        if not ENHANCED_MODULES_AVAILABLE:
            return jsonify({'error': 'cache module not available'}), 503
        return jsonify(get_cache_stats())

    # Alert system endpoints
    @app.route('/api/alerts')
    def api_alerts():
        if cfg.require_auth and not current_user():
            return jsonify({'error': 'unauthorized'}), 401
        if not ENHANCED_MODULES_AVAILABLE or alert_manager is None:
            return jsonify({'alerts': []})
        limit = int(request.args.get('limit', '100'))
        unack = request.args.get('unack', '0') == '1'
        # Keep it simple to avoid enum typing issues
        assert alert_manager is not None
        items = alert_manager.get_alerts(limit=limit, unacknowledged_only=unack)
        stats = alert_manager.get_alert_stats()
        return jsonify({'alerts': items, 'stats': stats})

    @app.route('/api/alerts/test', methods=['POST'])
    def api_test_alert():
        u = current_user()
        if not u:
            return jsonify({'error': 'unauthorized'}), 401
        if not ENHANCED_MODULES_AVAILABLE or alert_manager is None:
            return jsonify({'ok': False, 'error': 'alert module not available'}), 503
        results = alert_manager.test_notifications()
        return jsonify({'ok': True, 'results': results})

    @app.route('/api/alerts/acknowledge', methods=['POST'])
    def api_acknowledge_alert():
        u = current_user()
        if not u:
            return jsonify({'error': 'unauthorized'}), 401
        if not ENHANCED_MODULES_AVAILABLE or alert_manager is None:
            return jsonify({'ok': False, 'error': 'alert module not available'}), 503
        body = request.get_json(silent=True) or {}
        alert_id = body.get('alert_id')
        if not alert_id:
            return jsonify({'error': 'alert_id required'}), 400
        try:
            assert alert_manager is not None
            ok = alert_manager.acknowledge_alert(str(alert_id), acknowledged_by=u)
        except Exception:
            ok = False
        return jsonify({'ok': ok, 'acknowledged': alert_id})

    # Mobile webapp endpoints (placeholder for future enhancement)
    @app.route('/manifest.json')
    def app_manifest():
        manifest = {
            "name": "Guardia-AI",
            "short_name": "Guardia",
            "description": "Real-time AI security monitoring system",
            "start_url": "/",
            "display": "standalone",
            "orientation": "portrait-primary",
            "theme_color": "#1f2937",
            "background_color": "#0b0f14",
            "icons": [
                {
                    "src": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTkyIiBoZWlnaHQ9IjE5MiIgdmlld0JveD0iMCAwIDE5MiAxOTIiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxOTIiIGhlaWdodD0iMTkyIiBmaWxsPSIjMWYyOTM3Ii8+Cjx0ZXh0IHg9Ijk2IiB5PSIxMDAiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSI2MCIgZmlsbD0iI2VhZWNlZiIgdGV4dC1hbmNob3I9Im1pZGRsZSI+8J+boe+4jzwvdGV4dD4KPC9zdmc+",
                    "sizes": "192x192",
                    "type": "image/svg+xml",
                    "purpose": "any maskable"
                }
            ]
        }
        return jsonify(manifest)

    @app.route('/sw.js')
    def service_worker():
        sw_content = '''
// Basic service worker for Guardia-AI
const CACHE_NAME = 'guardia-ai-v1';
const urlsToCache = [
    '/',
    '/api/events',
    '/api/metrics',
    '/api/system'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => response || fetch(event.request))
    );
});
'''
        return Response(sw_content, mimetype='application/javascript')

    return app


if __name__ == '__main__':
    # basic CLI passthrough for source
    cfg = AppConfig()
    cfg.ensure_dirs()
    app = create_app(cfg)
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=False, threaded=True)

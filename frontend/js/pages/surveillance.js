/**
 * Surveillance Page — AegisWatch
 * Dual mode:
 * 1. 📡 Live Webcam CCTV — Real-time camera feed with browser capture & AI detection
 * 2. 🎬 Video Analysis — Visible video player with real-time synchronized AI bounding boxes,
 *    live timestamps, FPS counter, pause/resume, and event timeline.
 */

const surveillancePage = {
  // Live camera state
  _stream: null,
  _isCapturing: false,
  _captureInterval: null,
  _aiEnabled: true,
  _fps: 0,
  _fpsTimer: null,
  _frameCount: 0,
  _liveIncidents: [],

  // Video analysis state
  _selectedFile: null,
  _jobId: null,
  _pollInterval: null,
  _eventSource: null,
  _isPaused: false,
  _videoIncidents: [],

  async render() {
    return `
    <div class="fade-in">
      <!-- Page Header -->
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
        <div>
          <h2 style="margin:0 0 4px 0;">Live Surveillance &amp; Analysis</h2>
          <p style="margin:0;color:var(--text-secondary);font-size:0.85rem;">
            Real-time AI monitoring &middot; Live webcam CCTV &middot; Visible recorded-video analysis
          </p>
        </div>
        <!-- Tab Switcher -->
        <div style="display:flex;gap:4px;background:rgba(255,255,255,0.05);padding:4px;border-radius:8px;">
          <button id="tab-live" class="btn btn-sm" onclick="surveillancePage._switchTab('live')"
            style="color:var(--text-accent);border-bottom:2px solid var(--text-accent);border-radius:6px;padding:6px 16px;">
            📡 LIVE CCTV
          </button>
          <button id="tab-video" class="btn btn-sm" onclick="surveillancePage._switchTab('video')"
            style="color:var(--text-secondary);border-bottom:2px solid transparent;border-radius:6px;padding:6px 16px;">
            🎬 VIDEO ANALYSIS
          </button>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════════════
           TAB 1: LIVE WEBCAM CCTV
      ══════════════════════════════════════════════════════════ -->
      <div id="tab-content-live">
        <div style="display:grid;grid-template-columns:1fr 340px;gap:20px;">
          <!-- Camera Feed & Controls -->
          <div style="display:flex;flex-direction:column;gap:16px;">
            <div class="card" style="padding:16px;">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:8px;">
                  <span style="width:10px;height:10px;border-radius:50%;background:#fc4545;display:inline-block;" id="cam-status-dot"></span>
                  <strong id="cam-title">CAM-001 &mdash; Main Gate (Virtual Webcam)</strong>
                </div>
                <div style="display:flex;gap:8px;align-items:center;">
                  <span id="cam-status-label" style="font-size:0.75rem;color:var(--text-muted);">OFFLINE</span>
                  <span id="fps-display" style="font-size:0.75rem;font-family:var(--font-mono);color:var(--text-accent);">0 FPS</span>
                </div>
              </div>

              <!-- Viewport -->
              <div style="position:relative;background:#050811;border-radius:8px;overflow:hidden;aspect-ratio:16/9;display:flex;align-items:center;justify-content:center;border:1px solid rgba(255,255,255,0.08);">
                <video id="webcam-video" autoplay playsinline muted
                  style="width:100%;height:100%;object-fit:cover;display:block;"></video>
                <canvas id="detection-canvas"
                  style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></canvas>
                <div id="cam-overlay-msg"
                  style="position:absolute;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--text-secondary);background:rgba(10,14,26,0.85);inset:0;">
                  <div style="font-size:3rem;margin-bottom:12px;">📷</div>
                  <p style="margin:0;font-size:0.9rem;">Camera is offline</p>
                  <p style="margin:4px 0 0 0;font-size:0.75rem;color:var(--text-muted);">Click <strong>START CAMERA</strong> below to begin</p>
                </div>
              </div>

              <!-- Control Toolbar -->
              <div style="display:flex;align-items:center;justify-content:space-between;margin-top:14px;padding-top:14px;border-top:1px solid var(--border-color);flex-wrap:wrap;gap:10px;">
                <div style="display:flex;gap:10px;">
                  <button id="btn-start-cam" class="btn btn-primary" onclick="surveillancePage.startCamera()">
                    ▶ START CAMERA
                  </button>
                  <button id="btn-stop-cam" class="btn btn-secondary" onclick="surveillancePage.stopCamera()" disabled>
                    ■ STOP CAMERA
                  </button>
                  <button id="btn-snapshot" class="btn btn-ghost" onclick="surveillancePage.takeSnapshot()" disabled>
                    📸 SNAPSHOT
                  </button>
                </div>
                <div style="display:flex;align-items:center;gap:10px;">
                  <label style="display:flex;align-items:center;gap:6px;font-size:0.8rem;cursor:pointer;">
                    <input type="checkbox" id="chk-ai-enabled" checked onchange="surveillancePage.toggleAI(this.checked)">
                    AI Detection
                  </label>
                  <span id="ai-model-badge" class="badge badge-info" style="font-size:0.7rem;">YOLOv8n</span>
                </div>
              </div>
            </div>

            <!-- Risk Banner -->
            <div class="card" style="padding:14px;">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                <span style="font-size:0.75rem;font-weight:700;color:var(--text-secondary);">CURRENT SCENE RISK</span>
                <span id="live-risk-score" style="font-size:1.1rem;font-weight:800;color:var(--color-low);">0</span>
              </div>
              <div style="background:#1a2035;border-radius:4px;height:8px;overflow:hidden;">
                <div id="live-risk-bar" style="width:0%;height:100%;background:var(--color-low);transition:width 0.3s;"></div>
              </div>
            </div>
          </div>

          <!-- Live Sidebar (Objects & Alerts) -->
          <div style="display:flex;flex-direction:column;gap:16px;">
            <div class="card">
              <div class="card-header">
                <span class="card-title">🔍 Detected in Frame</span>
                <span id="det-count" style="font-size:0.72rem;color:var(--text-muted);">0 objects</span>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">
                <div style="text-align:center;padding:10px;background:rgba(255,255,255,0.03);border-radius:6px;">
                  <div style="font-size:1.4rem;font-weight:800;color:var(--color-low);" id="live-person-count">0</div>
                  <div style="font-size:0.68rem;color:var(--text-muted);">PERSONS</div>
                </div>
                <div style="text-align:center;padding:10px;background:rgba(255,255,255,0.03);border-radius:6px;">
                  <div style="font-size:1.4rem;font-weight:800;color:var(--text-accent);" id="live-object-count">0</div>
                  <div style="font-size:0.68rem;color:var(--text-muted);">OBJECTS</div>
                </div>
              </div>
              <div id="detection-list" style="font-size:0.8rem;max-height:160px;overflow-y:auto;">
                <div style="color:var(--text-muted);text-align:center;padding:20px;">Camera offline</div>
              </div>
            </div>

            <div class="card" style="flex:1;">
              <div class="card-header">
                <span class="card-title">🚨 AI Alerts (Session)</span>
                <button class="btn btn-ghost btn-sm" onclick="surveillancePage.clearLiveIncidents()">Clear</button>
              </div>
              <div id="live-incidents" style="font-size:0.8rem;max-height:280px;overflow-y:auto;">
                <div style="color:var(--text-muted);text-align:center;padding:20px;">No alerts yet</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════════════
           TAB 2: RECORDED VIDEO VISIBLE ANALYSIS
      ══════════════════════════════════════════════════════════ -->
      <div id="tab-content-video" style="display:none;">
        <div style="display:grid;grid-template-columns:1fr 380px;gap:20px;">
          <!-- Left Column: Upload / Video Player / Results -->
          <div style="display:flex;flex-direction:column;gap:16px;">
            
            <!-- Upload Card (Initial State) -->
            <div class="card" id="upload-card">
              <h3 style="margin-top:0;margin-bottom:16px;">📤 Upload Video for Visible Analysis</h3>
              <div id="drop-zone" style="
                border:2px dashed var(--border-color);border-radius:10px;
                padding:40px;text-align:center;cursor:pointer;
                transition:all 0.2s;background:rgba(255,255,255,0.02);"
                onclick="document.getElementById('video-file-input').click()"
                ondragover="surveillancePage._onDragOver(event)"
                ondragleave="surveillancePage._onDragLeave(event)"
                ondrop="surveillancePage._onDrop(event)">
                <div style="font-size:3rem;margin-bottom:12px;">🎬</div>
                <p style="color:var(--text-secondary);margin-bottom:8px;font-weight:600;">Drag &amp; drop a video file here, or click to browse</p>
                <p style="font-size:0.75rem;color:var(--text-muted);margin:0;">Supported: .mp4 &middot; .avi &middot; .mov &middot; .mkv &middot; .webm (max 500MB)</p>
                <input type="file" id="video-file-input" accept=".mp4,.avi,.mov,.mkv,.webm" style="display:none"
                  onchange="surveillancePage._onFileSelect(event)">
              </div>
              
              <div id="selected-file-info" style="display:none;margin-top:14px;padding:12px;background:rgba(255,255,255,0.04);border-radius:8px;">
                <div style="display:flex;align-items:center;justify-content:space-between;">
                  <div>
                    <div style="font-weight:600;font-size:0.9rem;" id="selected-filename">video.mp4</div>
                    <div style="font-size:0.72rem;color:var(--text-muted);" id="selected-filesize">0 MB</div>
                  </div>
                  <button class="btn btn-ghost btn-sm" onclick="surveillancePage._clearFile()">✕ Remove</button>
                </div>
              </div>

              <div style="margin-top:16px;display:flex;gap:10px;">
                <button id="btn-analyze" class="btn btn-primary" onclick="surveillancePage.startAnalysis()" disabled style="flex:1;">
                  🔍 START VISIBLE ANALYSIS
                </button>
              </div>
              <div style="margin-top:10px;font-size:0.7rem;color:var(--text-muted);">
                ℹ️ You will watch the video progress in real time with synchronized AI bounding boxes, tracking, and alerts.
              </div>
            </div>

            <!-- Visible Video Analysis Player (Shown during analysis) -->
            <div class="card" id="video-player-card" style="display:none;padding:16px;">
              <!-- Player Header -->
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;gap:8px;">
                <div style="display:flex;align-items:center;gap:8px;">
                  <span id="video-status-pill" class="badge badge-success" style="font-size:0.7rem;">ANALYZING</span>
                  <strong id="video-player-filename" style="font-size:0.9rem;">video.mp4</strong>
                </div>
                <div style="display:flex;align-items:center;gap:12px;">
                  <span id="video-fps-display" style="font-size:0.75rem;font-family:var(--font-mono);color:var(--text-accent);">0 FPS</span>
                  <span id="video-time-display" style="font-size:0.75rem;font-family:var(--font-mono);color:var(--text-secondary);">00:00 / 00:00</span>
                  <span id="video-model-badge" class="badge badge-info" style="font-size:0.7rem;">YOLOv8n</span>
                </div>
              </div>

              <!-- Video Viewport / Canvas Player -->
              <div id="video-viewport-container" style="position:relative;background:#050811;border-radius:8px;overflow:hidden;aspect-ratio:16/9;display:flex;align-items:center;justify-content:center;border:1px solid rgba(255,255,255,0.1);">
                <canvas id="video-analysis-canvas" style="width:100%;height:100%;display:block;object-fit:contain;"></canvas>
                <div id="video-buffering-msg" style="display:none;position:absolute;inset:0;background:rgba(10,14,26,0.7);display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--text-secondary);">
                  <div style="font-size:2rem;margin-bottom:8px;">⏳</div>
                  <span>Buffering frame...</span>
                </div>
              </div>

              <!-- Playback & Analysis Controls Toolbar -->
              <div style="margin-top:12px;display:flex;flex-direction:column;gap:10px;">
                <!-- Scrubber & Time Bar -->
                <div style="display:flex;align-items:center;gap:10px;">
                  <span id="video-scrubber-cur" style="font-family:var(--font-mono);font-size:0.75rem;min-width:38px;">00:00</span>
                  <div style="flex:1;background:rgba(255,255,255,0.08);height:8px;border-radius:4px;overflow:hidden;position:relative;">
                    <div id="video-progress-fill" style="width:0%;height:100%;background:var(--gradient-primary);border-radius:4px;transition:width 0.2s;"></div>
                  </div>
                  <span id="video-scrubber-tot" style="font-family:var(--font-mono);font-size:0.75rem;color:var(--text-muted);min-width:38px;">00:00</span>
                  <span id="video-pct-badge" style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--text-accent);min-width:34px;">0%</span>
                </div>

                <!-- Control Buttons -->
                <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
                  <div style="display:flex;gap:8px;">
                    <button id="btn-video-pause" class="btn btn-secondary btn-sm" onclick="surveillancePage.togglePauseVideo()">
                      ⏸ Pause
                    </button>
                    <button id="btn-video-stop" class="btn btn-ghost btn-sm" onclick="surveillancePage.cancelJob()" style="color:var(--color-critical);">
                      ⏹ Stop Analysis
                    </button>
                  </div>
                  <div style="font-size:0.75rem;color:var(--text-muted);" id="video-frame-counter">
                    Frame 0 / 0
                  </div>
                </div>
              </div>

              <!-- Live Detections & Risk Row (under player) -->
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px;padding-top:14px;border-top:1px solid var(--border-color);">
                <div>
                  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                    <span style="font-size:0.72rem;color:var(--text-muted);font-weight:700;">CURRENT DETECTIONS</span>
                    <span id="video-det-count" style="font-size:0.72rem;color:var(--text-accent);">0 items</span>
                  </div>
                  <div id="video-det-tags" style="display:flex;flex-wrap:wrap;gap:4px;min-height:24px;">
                    <span style="font-size:0.7rem;color:var(--text-muted);">None</span>
                  </div>
                </div>
                <div>
                  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                    <span style="font-size:0.72rem;color:var(--text-muted);font-weight:700;">SCENE RISK SCORE</span>
                    <span id="video-risk-val" style="font-size:0.85rem;font-weight:800;color:var(--color-low);">0%</span>
                  </div>
                  <div style="background:#1a2035;border-radius:4px;height:6px;overflow:hidden;">
                    <div id="video-risk-bar" style="width:0%;height:100%;background:var(--color-low);transition:width 0.3s;"></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Results Summary Card (Shown when done) -->
            <div class="card" id="results-summary" style="display:none;">
              <h3 style="margin-top:0;margin-bottom:16px;">📊 Analysis Results</h3>
              <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px;">
                <div style="text-align:center;padding:12px;background:rgba(255,255,255,0.04);border-radius:8px;">
                  <div style="font-size:1.5rem;font-weight:800;color:var(--text-accent);" id="result-events">0</div>
                  <div style="font-size:0.68rem;color:var(--text-muted);">EVENTS DETECTED</div>
                </div>
                <div style="text-align:center;padding:12px;background:rgba(255,255,255,0.04);border-radius:8px;">
                  <div style="font-size:1.5rem;font-weight:800;color:var(--color-high);" id="result-incidents">0</div>
                  <div style="font-size:0.68rem;color:var(--text-muted);">INCIDENTS CREATED</div>
                </div>
                <div style="text-align:center;padding:12px;background:rgba(255,255,255,0.04);border-radius:8px;">
                  <div style="font-size:1.5rem;font-weight:800;color:var(--color-low);" id="result-frames">0</div>
                  <div style="font-size:0.68rem;color:var(--text-muted);">FRAMES PROCESSED</div>
                </div>
              </div>
              <div style="display:flex;gap:10px;">
                <button class="btn btn-primary" onclick="window.navigate('incidents')">View Incidents &rarr;</button>
                <button class="btn btn-secondary" onclick="surveillancePage._resetUpload()">Analyze Another Video</button>
              </div>
            </div>
          </div>

          <!-- Right Column: Event Timeline -->
          <div class="card" style="height:fit-content;max-height:85vh;overflow-y:auto;">
            <div class="card-header">
              <span class="card-title">📅 Event Timeline</span>
              <span id="timeline-count" style="font-size:0.72rem;color:var(--text-muted);">0 events</span>
            </div>
            <div id="event-timeline" style="font-size:0.8rem;">
              <div style="color:var(--text-muted);text-align:center;padding:30px;">Upload a video to see detected events here</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    `;
  },

  async init() {
    this._selectedFile = null;
    this._aiEnabled = true;
    this._liveIncidents = [];
    this._videoIncidents = [];
    this._isPaused = false;
  },

  destroy() {
    this.stopCamera();
    if (this._eventSource) {
      this._eventSource.close();
      this._eventSource = null;
    }
    if (this._pollInterval) {
      clearInterval(this._pollInterval);
      this._pollInterval = null;
    }
  },

  _switchTab(tab) {
    const isLive = tab === 'live';
    const cLive = document.getElementById('tab-content-live');
    const cVideo = document.getElementById('tab-content-video');
    if (cLive) cLive.style.display = isLive ? '' : 'none';
    if (cVideo) cVideo.style.display = isLive ? 'none' : '';

    const tabLive = document.getElementById('tab-live');
    const tabVideo = document.getElementById('tab-video');
    if (tabLive && tabVideo) {
      if (isLive) {
        tabLive.style.color = 'var(--text-accent)';
        tabLive.style.borderBottom = '2px solid var(--text-accent)';
        tabVideo.style.color = 'var(--text-secondary)';
        tabVideo.style.borderBottom = '2px solid transparent';
      } else {
        tabVideo.style.color = 'var(--text-accent)';
        tabVideo.style.borderBottom = '2px solid var(--text-accent)';
        tabLive.style.color = 'var(--text-secondary)';
        tabLive.style.borderBottom = '2px solid transparent';
      }
    }

    if (!isLive) this.stopCamera();
  },

  // ─── LIVE WEBCAM ───────────────────────────────────────────────

  async startCamera() {
    const startBtn = document.getElementById('btn-start-cam');
    const stopBtn  = document.getElementById('btn-stop-cam');
    const snapBtn  = document.getElementById('btn-snapshot');
    const overlay  = document.getElementById('cam-overlay-msg');
    const video    = document.getElementById('webcam-video');
    const statusDot = document.getElementById('cam-status-dot');
    const statusLbl = document.getElementById('cam-status-label');

    try {
      if (statusLbl) statusLbl.textContent = 'Requesting permission...';
      this._stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'environment' },
        audio: false
      });
      video.srcObject = this._stream;
      await video.play();

      if (overlay) overlay.style.display = 'none';
      if (statusDot) statusDot.style.background = '#68d391';
      if (statusLbl) statusLbl.textContent = 'ONLINE';
      if (startBtn) startBtn.disabled = true;
      if (stopBtn)  stopBtn.disabled  = false;
      if (snapBtn)  snapBtn.disabled  = false;

      this._isCapturing = true;
      this._frameCount  = 0;
      this._fpsTimer    = setInterval(() => {
        this._fps = this._frameCount;
        this._frameCount = 0;
        const el = document.getElementById('fps-display');
        if (el) el.textContent = `${this._fps} FPS`;
      }, 1000);

      this._captureInterval = setInterval(() => {
        if (this._isCapturing && this._aiEnabled) {
          this._sendFrame();
        }
      }, 2000);

      try {
        const cams = await window.api.getCameras();
        const cam001 = (Array.isArray(cams) ? cams : cams.cameras || []).find(c => c.camera_id === 'CAM-001');
        if (cam001) window.api.put(`/api/cameras/${cam001.id}`, { status: 'ONLINE' }).catch(() => {});
      } catch (e) {}

    } catch (err) {
      let msg = 'Camera error';
      if (err.name === 'NotAllowedError') msg = '❌ Camera permission denied.';
      else if (err.name === 'NotFoundError') msg = '❌ No camera found.';
      else if (err.name === 'NotReadableError') msg = '❌ Camera already in use.';
      else msg = `❌ ${err.message}`;

      if (overlay) {
        overlay.innerHTML = `<div style="font-size:2rem;margin-bottom:12px;">⚠️</div><p style="color:#fc4545;text-align:center;max-width:280px;">${msg}</p>`;
        overlay.style.display = 'flex';
      }
      if (statusDot) statusDot.style.background = '#fc4545';
      if (statusLbl) statusLbl.textContent = 'ERROR';
    }
  },

  stopCamera() {
    clearInterval(this._captureInterval);
    clearInterval(this._fpsTimer);
    this._captureInterval = null;
    this._isCapturing = false;

    if (this._stream) {
      this._stream.getTracks().forEach(t => t.stop());
      this._stream = null;
    }

    const video    = document.getElementById('webcam-video');
    const overlay  = document.getElementById('cam-overlay-msg');
    const startBtn = document.getElementById('btn-start-cam');
    const stopBtn  = document.getElementById('btn-stop-cam');
    const snapBtn  = document.getElementById('btn-snapshot');
    const statusDot = document.getElementById('cam-status-dot');
    const statusLbl = document.getElementById('cam-status-label');

    if (video)   { video.srcObject = null; }
    if (overlay) {
      overlay.innerHTML = `<div style="font-size:3rem;margin-bottom:12px;">📷</div><p style="color:var(--text-secondary);text-align:center;max-width:280px;">Camera stopped. Click <strong>START CAMERA</strong> to resume.</p>`;
      overlay.style.display = 'flex';
    }
    if (startBtn) startBtn.disabled = false;
    if (stopBtn)  stopBtn.disabled  = true;
    if (snapBtn)  snapBtn.disabled  = true;
    if (statusDot) statusDot.style.background = '#fc4545';
    if (statusLbl) statusLbl.textContent = 'OFFLINE';
  },

  toggleAI(enabled) {
    this._aiEnabled = enabled;
    const badge = document.getElementById('ai-model-badge');
    if (badge) {
      badge.textContent = enabled ? 'YOLOv8n' : 'PAUSED';
      badge.className = `badge ${enabled ? 'badge-info' : 'badge-warning'}`;
    }
  },

  async _sendFrame() {
    const video  = document.getElementById('webcam-video');
    const canvas = document.getElementById('detection-canvas');
    if (!video || !canvas || video.readyState < 2) return;

    this._frameCount++;
    canvas.width  = video.videoWidth  || 640;
    canvas.height = video.videoHeight || 480;

    const offscreen = document.createElement('canvas');
    offscreen.width  = 640;
    offscreen.height = 480;
    const offCtx = offscreen.getContext('2d');
    offCtx.drawImage(video, 0, 0, 640, 480);
    const b64 = offscreen.toDataURL('image/jpeg', 0.6).split(',')[1];

    try {
      const result = await window.api.post('/api/surveillance/webcam-frame', {
        frame_base64: b64,
        camera_id: 'CAM-001',
        timestamp: new Date().toISOString()
      });

      if (result) {
        this._renderLiveDetections(result, canvas, video);
        this._updateRiskDisplay(result.risk_score || 0);
      }
    } catch (e) {}
  },

  _renderLiveDetections(result, canvas, video) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const detections = result.detections || [];
    const scaleX = canvas.width  / (video.videoWidth  || canvas.width);
    const scaleY = canvas.height / (video.videoHeight || canvas.height);

    const colorMap = { person: '#68d391', backpack: '#f6ad55', handbag: '#f6ad55', knife: '#fc4545', default: '#63b3ed' };

    detections.forEach(det => {
      const [x1,y1,x2,y2] = (det.bbox || [0,0,0,0]).map((v,i) => v * (i%2===0 ? scaleX : scaleY));
      const color = colorMap[det.class_name] || colorMap.default;
      const w = x2-x1, h = y2-y1;

      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(x1, y1, w, h);

      const label = `${det.class_name} #${det.track_id || ''} ${Math.round((det.confidence||0)*100)}%`;
      ctx.font = '11px Inter, sans-serif';
      const tw = ctx.measureText(label).width;
      ctx.fillStyle = color + 'cc';
      ctx.fillRect(x1, y1 - 18, tw + 8, 18);
      ctx.fillStyle = '#000';
      ctx.fillText(label, x1 + 4, y1 - 4);
    });

    const persons = detections.filter(d => d.class_name === 'person').length;
    const pcEl = document.getElementById('live-person-count');
    if (pcEl) pcEl.textContent = persons;

    const objects = detections.filter(d => d.class_name !== 'person').length;
    const ocEl = document.getElementById('live-object-count');
    if (ocEl) ocEl.textContent = objects;

    const listEl = document.getElementById('detection-list');
    const dcEl   = document.getElementById('det-count');
    if (dcEl) dcEl.textContent = `${detections.length} objects`;
    if (listEl) {
      if (detections.length === 0) {
        listEl.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:20px;">No detections in frame</div>';
      } else {
        listEl.innerHTML = detections.map(det => `
          <div style="display:flex;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border-color);">
            <div>
              <span style="font-weight:600;">${det.class_name}</span>
              <span style="color:var(--text-muted);margin-left:6px;">#${det.track_id || '?'}</span>
            </div>
            <span style="color:var(--text-accent);">${Math.round((det.confidence||0)*100)}%</span>
          </div>`).join('');
      }
    }

    if (result.incidents_created && result.incidents_created.length > 0) {
      result.incidents_created.forEach(inc => {
        this._liveIncidents.unshift(inc);
        if (this._liveIncidents.length > 20) this._liveIncidents.pop();
      });
      this._renderLiveIncidents();
    }
  },

  _renderLiveIncidents() {
    const el = document.getElementById('live-incidents');
    if (!el) return;
    if (this._liveIncidents.length === 0) {
      el.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:16px;">No alerts</div>';
      return;
    }
    const icons = { FIGHT:'👊', THEFT:'💼', LOITERING:'⏱️', INTRUSION:'🚫', ABANDONED_OBJECT:'🎒', SUSPICIOUS_MOVEMENT:'🏃' };
    el.innerHTML = this._liveIncidents.map(inc => `
      <div style="padding:8px;margin-bottom:6px;background:rgba(252,69,69,0.08);border:1px solid rgba(252,69,69,0.2);border-radius:6px;">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
          <span>${icons[inc.incident_type] || '⚠️'}</span>
          <strong style="font-size:0.78rem;">${(inc.incident_type||'').replace(/_/g,' ')}</strong>
          <span class="badge badge-${(inc.severity||'medium').toLowerCase()}" style="margin-left:auto;font-size:0.62rem;">${inc.severity||''}</span>
        </div>
        <div style="font-size:0.7rem;color:var(--text-muted);">Risk: ${inc.risk_score||0}% &middot; Confidence: ${inc.confidence||0}%</div>
        ${inc.incident_id ? `<div style="font-size:0.68rem;color:var(--text-accent);margin-top:4px;">ID: ${inc.incident_id}</div>` : ''}
      </div>`).join('');
  },

  _updateRiskDisplay(score) {
    const scoreEl = document.getElementById('live-risk-score');
    const barEl   = document.getElementById('live-risk-bar');
    if (scoreEl) {
      scoreEl.textContent = Math.round(score);
      scoreEl.style.color = score > 70 ? '#fc4545' : score > 40 ? '#f6ad55' : '#68d391';
    }
    if (barEl) {
      barEl.style.width = `${Math.min(100, score)}%`;
      barEl.style.background = score > 70 ? 'var(--color-critical)' : score > 40 ? 'var(--color-high)' : 'var(--color-low)';
    }
  },

  takeSnapshot() {
    const video = document.getElementById('webcam-video');
    if (!video) return;
    const snap = document.createElement('canvas');
    snap.width  = video.videoWidth  || 640;
    snap.height = video.videoHeight || 480;
    snap.getContext('2d').drawImage(video, 0, 0);
    const link = document.createElement('a');
    link.download = `snapshot_${Date.now()}.jpg`;
    link.href = snap.toDataURL('image/jpeg');
    link.click();
  },

  // ─── RECORDED VIDEO ANALYSIS ───────────────────────────────────

  _onDragOver(e) {
    e.preventDefault();
    document.getElementById('drop-zone').style.borderColor = 'var(--text-accent)';
  },

  _onDragLeave(e) {
    e.preventDefault();
    document.getElementById('drop-zone').style.borderColor = 'var(--border-color)';
  },

  _onDrop(e) {
    e.preventDefault();
    document.getElementById('drop-zone').style.borderColor = 'var(--border-color)';
    const files = e.dataTransfer.files;
    if (files.length > 0) this._handleFile(files[0]);
  },

  _onFileSelect(e) {
    if (e.target.files.length > 0) this._handleFile(e.target.files[0]);
  },

  _handleFile(file) {
    const allowed = ['.mp4', '.avi', '.mov', '.mkv', '.webm'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) {
      alert(`Unsupported file type: ${ext}. Please upload a video file.`);
      return;
    }
    this._selectedFile = file;
    document.getElementById('selected-filename').textContent = file.name;
    document.getElementById('selected-filesize').textContent = `${(file.size / (1024*1024)).toFixed(1)} MB`;
    document.getElementById('selected-file-info').style.display = '';
    document.getElementById('drop-zone').style.display = 'none';
    document.getElementById('btn-analyze').disabled = false;
  },

  _clearFile() {
    this._selectedFile = null;
    document.getElementById('video-file-input').value = '';
    document.getElementById('selected-file-info').style.display = 'none';
    document.getElementById('drop-zone').style.display = '';
    document.getElementById('btn-analyze').disabled = true;
  },

  async startAnalysis() {
    if (!this._selectedFile) return;

    const btn = document.getElementById('btn-analyze');
    btn.disabled = true;
    btn.textContent = '⏳ Uploading...';

    try {
      const formData = new FormData();
      formData.append('file', this._selectedFile);

      const token = window.api.getToken();
      const resp = await fetch('/api/surveillance/upload-video', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || 'Upload failed');
      }

      const data = await resp.json();
      this._jobId = data.job_id;
      this._isPaused = false;
      this._videoIncidents = [];

      // Switch to visible player card
      document.getElementById('upload-card').style.display = 'none';
      document.getElementById('results-summary').style.display = 'none';
      const playerCard = document.getElementById('video-player-card');
      playerCard.style.display = '';
      document.getElementById('video-player-filename').textContent = this._selectedFile.name;

      // Reset HUD / canvas
      const canvas = document.getElementById('video-analysis-canvas');
      if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
      this._updatePlayerHUD({
        status: 'ANALYZING',
        fps: 0,
        progress: 0,
        timestamp_str: '00:00',
        total_duration_str: '00:00',
        frame_num: 0,
        total_frames: 0
      });

      // Clear timeline
      document.getElementById('event-timeline').innerHTML =
        '<div style="color:var(--text-muted);text-align:center;padding:20px;">⏳ Watching analysis in real time...</div>';
      document.getElementById('timeline-count').textContent = '0 events';

      // Connect real-time Server-Sent Events (SSE) stream
      this._connectJobStream(this._jobId);

      // Also set fallback poll timer in case SSE is interrupted
      this._pollInterval = setInterval(() => this._pollJob(), 2500);

    } catch (e) {
      btn.disabled = false;
      btn.textContent = '🔍 START VISIBLE ANALYSIS';
      alert('Upload failed: ' + e.message);
    }
  },

  _connectJobStream(jobId) {
    if (this._eventSource) {
      this._eventSource.close();
      this._eventSource = null;
    }

    try {
      this._eventSource = new EventSource(`/api/surveillance/job/${jobId}/stream`);

      this._eventSource.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          this._handleStreamMessage(data);
        } catch (err) {
          console.error('SSE JSON error:', err);
        }
      };

      this._eventSource.onerror = (err) => {
        // SSE error or stream closed; fallback poll continues
      };
    } catch (err) {
      console.warn('EventSource not supported, using polling fallback');
    }
  },

  _handleStreamMessage(data) {
    if (data.type === 'frame' || data.type === 'state') {
      this._renderVisibleFrame(data);
    } else if (data.type === 'paused') {
      this._isPaused = true;
      const btn = document.getElementById('btn-video-pause');
      const pill = document.getElementById('video-status-pill');
      if (btn) btn.innerHTML = '▶ Resume';
      if (pill) { pill.textContent = 'PAUSED'; pill.className = 'badge badge-warning'; }
    } else if (data.type === 'resumed') {
      this._isPaused = false;
      const btn = document.getElementById('btn-video-pause');
      const pill = document.getElementById('video-status-pill');
      if (btn) btn.innerHTML = '⏸ Pause';
      if (pill) { pill.textContent = 'ANALYZING'; pill.className = 'badge badge-success'; }
    } else if (data.type === 'finished' || data.type === 'completed' || data.type === 'cancelled' || data.type === 'failed') {
      if (this._eventSource) {
        this._eventSource.close();
        this._eventSource = null;
      }
      if (this._pollInterval) {
        clearInterval(this._pollInterval);
        this._pollInterval = null;
      }
      this._onJobDone(data);
    }
  },

  _renderVisibleFrame(data) {
    const canvas = document.getElementById('video-analysis-canvas');
    if (!canvas) return;

    // 1. Draw frame if base64 provided
    if (data.frame_b64) {
      const img = new Image();
      img.onload = () => {
        if (canvas.width !== img.naturalWidth || canvas.height !== img.naturalHeight) {
          canvas.width  = img.naturalWidth  || 640;
          canvas.height = img.naturalHeight || 480;
        }
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        // 2. Render real-time AI bounding boxes on canvas
        const detections = data.detections || [];
        const scaleX = canvas.width  / (img.naturalWidth  || canvas.width);
        const scaleY = canvas.height / (img.naturalHeight || canvas.height);

        const colorMap = {
          person: '#68d391',
          backpack: '#f6ad55',
          handbag: '#f6ad55',
          suitcase: '#f6ad55',
          laptop: '#f6ad55',
          knife: '#fc4545',
          scissors: '#fc4545',
          default: '#63b3ed'
        };

        detections.forEach(det => {
          const [x1, y1, x2, y2] = (det.bbox || [0,0,0,0]).map((v, i) => v * (i % 2 === 0 ? scaleX : scaleY));
          const color = colorMap[det.class_name] || colorMap.default;
          const w = x2 - x1;
          const h = y2 - y1;

          ctx.strokeStyle = color;
          ctx.lineWidth = 2.5;
          ctx.strokeRect(x1, y1, w, h);

          // Foot marker dot
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(x1 + w / 2, y2, 3, 0, Math.PI * 2);
          ctx.fill();

          // Label badge
          const trackStr = det.track_id !== undefined && det.track_id !== null ? ` #${det.track_id}` : '';
          const confStr = `${Math.round((det.confidence || 0) * 100)}%`;
          const label = `${det.class_name}${trackStr} [${confStr}]`;

          ctx.font = 'bold 11px Inter, sans-serif';
          const tw = ctx.measureText(label).width;
          ctx.fillStyle = color + 'ee';
          ctx.fillRect(x1, Math.max(0, y1 - 20), tw + 8, 20);
          ctx.fillStyle = '#0a0e1a';
          ctx.fillText(label, x1 + 4, Math.max(14, y1 - 5));
        });

        // 3. Corner HUD timestamp on canvas
        ctx.fillStyle = 'rgba(10, 14, 26, 0.75)';
        ctx.fillRect(10, 10, 160, 24);
        ctx.fillStyle = '#63b3ed';
        ctx.font = '11px monospace';
        ctx.fillText(`⏱ ${data.timestamp_str || '00:00'} | Frame ${data.frame_num || 0}`, 16, 26);
      };
      img.src = 'data:image/jpeg;base64,' + data.frame_b64;
    }

    // 4. Update HUD and controls
    this._updatePlayerHUD(data);

    // 5. Update live detections pill list
    const tagsEl = document.getElementById('video-det-tags');
    const detCountEl = document.getElementById('video-det-count');
    const detections = data.detections || [];
    if (detCountEl) detCountEl.textContent = `${detections.length} item${detections.length !== 1 ? 's' : ''}`;
    if (tagsEl) {
      if (detections.length === 0) {
        tagsEl.innerHTML = '<span style="font-size:0.7rem;color:var(--text-muted);">No objects in frame</span>';
      } else {
        tagsEl.innerHTML = detections.map(d => `
          <span style="font-size:0.68rem;padding:2px 8px;border-radius:4px;background:rgba(255,255,255,0.06);border:1px solid var(--border-color);">
            <strong>${d.class_name}</strong> #${d.track_id !== undefined ? d.track_id : '?'}
            <span style="color:var(--text-accent);">${Math.round((d.confidence||0)*100)}%</span>
          </span>
        `).join('');
      }
    }

    // 6. Update Risk Meter
    const risk = data.risk_score || 0;
    const riskVal = document.getElementById('video-risk-val');
    const riskBar = document.getElementById('video-risk-bar');
    if (riskVal) {
      riskVal.textContent = `${Math.round(risk)}% (${data.risk_level || 'LOW'})`;
      riskVal.style.color = risk > 70 ? '#fc4545' : risk > 40 ? '#f6ad55' : '#68d391';
    }
    if (riskBar) {
      riskBar.style.width = `${Math.min(100, risk)}%`;
      riskBar.style.background = risk > 70 ? 'var(--color-critical)' : risk > 40 ? 'var(--color-high)' : 'var(--color-low)';
    }

    // 7. Process new incidents
    const newIncs = data.new_incidents || (data.incidents_created || []);
    if (newIncs.length > 0) {
      newIncs.forEach(inc => {
        this._videoIncidents.push(inc);
      });
      this._renderTimeline(this._videoIncidents);
      if (window.showSuccessToast) {
        window.showSuccessToast(`🚨 Incident detected: ${newIncs[0].incident_type}`);
      }
    }
  },

  _updatePlayerHUD(data) {
    const fpsEl   = document.getElementById('video-fps-display');
    const timeEl  = document.getElementById('video-time-display');
    const curScrub = document.getElementById('video-scrubber-cur');
    const totScrub = document.getElementById('video-scrubber-tot');
    const pctBadge = document.getElementById('video-pct-badge');
    const fillEl  = document.getElementById('video-progress-fill');
    const frameEl = document.getElementById('video-frame-counter');
    const modelBadge = document.getElementById('video-model-badge');

    const pct = Math.round(data.progress || 0);
    const ts  = data.timestamp_str || '00:00';
    const tot = data.total_duration_str || '00:00';

    if (fpsEl)   fpsEl.textContent = `${data.fps || 0} FPS`;
    if (timeEl)  timeEl.textContent = `${ts} / ${tot}`;
    if (curScrub) curScrub.textContent = ts;
    if (totScrub) totScrub.textContent = tot;
    if (pctBadge) pctBadge.textContent = `${pct}%`;
    if (fillEl)  fillEl.style.width = `${pct}%`;
    if (frameEl) frameEl.textContent = `Frame ${data.frame_num || 0} / ${data.total_frames || 0}`;
    if (modelBadge && data.model) modelBadge.textContent = data.model;
  },

  async togglePauseVideo() {
    if (!this._jobId) return;
    try {
      const btn = document.getElementById('btn-video-pause');
      const pill = document.getElementById('video-status-pill');

      if (this._isPaused) {
        await window.api.resumeSurveillanceJob(this._jobId);
        this._isPaused = false;
        if (btn) btn.innerHTML = '⏸ Pause';
        if (pill) { pill.textContent = 'ANALYZING'; pill.className = 'badge badge-success'; }
      } else {
        await window.api.pauseSurveillanceJob(this._jobId);
        this._isPaused = true;
        if (btn) btn.innerHTML = '▶ Resume';
        if (pill) { pill.textContent = 'PAUSED'; pill.className = 'badge badge-warning'; }
      }
    } catch (e) {
      console.error('Pause toggle error:', e);
    }
  },

  async _pollJob() {
    if (!this._jobId) return;
    try {
      const job = await window.api.getSurveillanceJob(this._jobId);

      // If SSE isn't active or dropped, update frame and HUD from REST
      if (job.current_frame_b64) {
        this._renderVisibleFrame({
          type: 'frame',
          job_id: this._jobId,
          status: job.status,
          progress: job.progress,
          frame_b64: job.current_frame_b64,
          detections: job.current_detections || [],
          risk_score: job.current_risk_score || 0,
          risk_level: job.current_risk_level || 'LOW',
          timestamp_sec: job.current_timestamp_sec || 0,
          timestamp_str: job.current_timestamp_str || '00:00',
          total_duration_str: job.video_duration_str || '00:00',
          fps: job.fps || 0,
          frame_num: job.current_frame_num || 0,
          total_frames: job.total_frames || 0,
          model: job.model || 'YOLOv8n',
          incidents: job.incidents || []
        });
      }

      if (job.incidents && job.incidents.length > 0) {
        this._videoIncidents = job.incidents;
        this._renderTimeline(this._videoIncidents);
      }

      if (job.status === 'COMPLETED' || job.status === 'FAILED' || job.status === 'CANCELLED') {
        clearInterval(this._pollInterval);
        this._pollInterval = null;
        if (this._eventSource) {
          this._eventSource.close();
          this._eventSource = null;
        }
        this._onJobDone(job);
      }
    } catch (e) {
      console.error('Poll error:', e);
    }
  },

  _onJobDone(job) {
    const pill = document.getElementById('video-status-pill');
    if (pill) {
      if (job.status === 'COMPLETED') {
        pill.textContent = 'COMPLETED';
        pill.className = 'badge badge-info';
      } else if (job.status === 'CANCELLED') {
        pill.textContent = 'STOPPED';
        pill.className = 'badge badge-warning';
      } else {
        pill.textContent = 'FAILED';
        pill.className = 'badge badge-danger';
      }
    }

    // Show summary card
    document.getElementById('results-summary').style.display = '';

    const events = (job.incidents || this._videoIncidents || []).length;
    const el1 = document.getElementById('result-events');
    const el2 = document.getElementById('result-incidents');
    const el3 = document.getElementById('result-frames');
    if (el1) el1.textContent = events;
    if (el2) el2.textContent = events;
    if (el3) el3.textContent = job.total_frames || '—';

    if (events > 0) {
      this._renderTimeline(job.incidents || this._videoIncidents);
    } else {
      const tl = document.getElementById('event-timeline');
      if (tl) tl.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:30px;">✅ Analysis complete. No suspicious events detected in video.</div>';
    }
  },

  _renderTimeline(events) {
    const el = document.getElementById('event-timeline');
    const cntEl = document.getElementById('timeline-count');
    if (!el) return;
    if (cntEl) cntEl.textContent = `${events.length} event${events.length !== 1 ? 's' : ''}`;

    const icons = { FIGHT:'👊', THEFT:'💼', LOITERING:'⏱️', INTRUSION:'🚫', ABANDONED_OBJECT:'🎒', SUSPICIOUS_MOVEMENT:'🏃', WEAPON_DETECTED:'🔫' };
    const severityColors = { CRITICAL:'#fc4545', HIGH:'#f6ad55', MEDIUM:'#fbbf24', LOW:'#68d391' };

    el.innerHTML = events.map((ev) => {
      const color = severityColors[ev.severity] || '#63b3ed';
      const ts = ev.timestamp_str || (ev.timestamp_sec ? `${Math.round(ev.timestamp_sec)}s` : '');
      return `
        <div style="
          padding:12px;margin-bottom:8px;
          border-left:3px solid ${color};
          background:rgba(255,255,255,0.03);
          border-radius:0 6px 6px 0;
          cursor:pointer;
          transition:background 0.15s;"
          onclick="${ev.incident_id ? `window.navigate('incidents')` : ''}"
          onmouseover="this.style.background='rgba(255,255,255,0.06)'"
          onmouseout="this.style.background='rgba(255,255,255,0.03)'">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="font-size:1.1rem;">${icons[ev.incident_type] || '⚠️'}</span>
              <strong style="font-size:0.82rem;">${(ev.incident_type||'').replace(/_/g,' ')}</strong>
            </div>
            <div style="font-family:var(--font-mono);font-size:0.72rem;color:${color};">${ts}</div>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <span style="font-size:0.68rem;padding:2px 6px;border-radius:3px;background:${color}22;color:${color};">${ev.severity || '—'}</span>
            <span style="font-size:0.68rem;color:var(--text-muted);">Risk: ${ev.risk_score || 0}%</span>
            <span style="font-size:0.68rem;color:var(--text-muted);">Confidence: ${Math.round(ev.ai_confidence || ev.confidence || 0)}%</span>
          </div>
          ${ev.incident_id ? `<div style="font-size:0.68rem;color:var(--text-accent);margin-top:4px;">→ View ${ev.incident_id} in Incidents</div>` : ''}
        </div>`;
    }).join('');
  },

  async cancelJob() {
    if (!this._jobId) return;
    try {
      await window.api.cancelSurveillanceJob(this._jobId);
      if (this._eventSource) {
        this._eventSource.close();
        this._eventSource = null;
      }
      if (this._pollInterval) {
        clearInterval(this._pollInterval);
        this._pollInterval = null;
      }
      this._onJobDone({
        status: 'CANCELLED',
        message: 'Analysis stopped by user',
        incidents: this._videoIncidents
      });
    } catch (e) {
      console.error('Cancel error:', e);
    }
  },

  _resetUpload() {
    if (this._eventSource) {
      this._eventSource.close();
      this._eventSource = null;
    }
    if (this._pollInterval) {
      clearInterval(this._pollInterval);
      this._pollInterval = null;
    }
    this._jobId = null;
    this._selectedFile = null;
    this._videoIncidents = [];
    this._isPaused = false;

    document.getElementById('upload-card').style.display = '';
    document.getElementById('video-player-card').style.display = 'none';
    document.getElementById('results-summary').style.display = 'none';
    document.getElementById('drop-zone').style.display = '';
    document.getElementById('selected-file-info').style.display = 'none';
    document.getElementById('btn-analyze').disabled = true;
    document.getElementById('video-file-input').value = '';
    document.getElementById('event-timeline').innerHTML =
      '<div style="color:var(--text-muted);text-align:center;padding:30px;">Upload a video to see detected events here</div>';
    document.getElementById('btn-analyze').textContent = '🔍 START VISIBLE ANALYSIS';
  },
};

window.surveillancePage = surveillancePage;

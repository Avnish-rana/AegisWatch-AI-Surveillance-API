const livePage = {
  _cameras: [],
  _gridSize: '2x2',
  
  async render() {
    return `
      <style>
        .live-grid { display: grid; gap: 16px; height: calc(100vh - 200px); }
        .grid-1x1 { grid-template-columns: 1fr; grid-template-rows: 1fr; }
        .grid-2x2 { grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; }
        .grid-3x3 { grid-template-columns: 1fr 1fr 1fr; grid-template-rows: 1fr 1fr 1fr; }
        
        .feed-item { position: relative; background: #000; border: 1px solid #2d3748; border-radius: 8px; overflow: hidden; display: flex; align-items: center; justify-content: center; cursor: pointer; }
        .feed-item:hover { border-color: #63b3ed; }
        .feed-item img { width: 100%; height: 100%; object-fit: contain; }
        .feed-label { position: absolute; bottom: 12px; left: 12px; background: rgba(0,0,0,0.7); padding: 6px 12px; border-radius: 4px; font-size: 14px; display: flex; align-items: center; gap: 8px; pointer-events: none; }
        .live-badge { background: #fc4545; color: #fff; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 3px; animation: blink 2s infinite; }
        .feed-no-signal { display: flex; flex-direction: column; align-items: center; color: #718096; }
        .feed-no-signal .icon { font-size: 32px; margin-bottom: 8px; opacity: 0.5; }
        
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
      </style>
      
      <div class="fade-in">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
          <h2>Live Monitoring</h2>
          <div style="display:flex;gap:12px;align-items:center;">
            <select id="live-camera-select" class="input" onchange="window.livePage.focusCamera(this.value)">
              <option value="">-- Focus Camera --</option>
            </select>
            <div class="tabs" style="border:1px solid #2d3748;border-radius:6px;overflow:hidden;display:flex;">
              <button class="btn" style="border-radius:0;border:none;" onclick="window.livePage.setGrid('1x1')">1x1</button>
              <button class="btn" style="border-radius:0;border:none;border-left:1px solid #2d3748;" onclick="window.livePage.setGrid('2x2')">2x2</button>
              <button class="btn" style="border-radius:0;border:none;border-left:1px solid #2d3748;" onclick="window.livePage.setGrid('3x3')">3x3</button>
            </div>
          </div>
        </div>
        
        <div id="live-feeds-container" class="live-grid grid-2x2">
          <!-- Feeds injected here -->
        </div>
      </div>
      
      <!-- Maximize Modal -->
      <div id="maximize-modal" class="modal" style="display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;background:#000;z-index:2000;align-items:center;justify-content:center;flex-direction:column;" onclick="livePage._closeMaximize(event)">
        <div style="width:100%;display:flex;justify-content:flex-end;padding:12px 20px;position:absolute;top:0;left:0;box-sizing:border-box;z-index:3000;" onclick="event.stopPropagation()">
          <button class="btn" id="btn-native-fullscreen" style="background:rgba(255,255,255,0.12);color:#fff;margin-right:8px;" onclick="livePage._toggleNativeFullscreen()">&#x26F6; Full Screen</button>
          <button class="btn" style="background:rgba(220,50,50,0.6);color:#fff;" onclick="livePage._closeMaximize()">&#x2715; Close</button>
        </div>
        <div id="maximize-content" style="width:95%;height:90vh;display:flex;align-items:center;justify-content:center;position:relative;"></div>
      </div>
    `;
  },
  
  async init() {
    try {
      this._cameras = await window.api.getCameras();
      this._cameras = this._cameras.filter(c => c.status !== 'DISABLED'); // only active feeds
      
      const select = document.getElementById('live-camera-select');
      if (select) {
        this._cameras.forEach(c => {
          const opt = document.createElement('option');
          opt.value = c.id;
          opt.innerText = `${c.camera_id} - ${c.name}`;
          select.appendChild(opt);
        });
      }
      
      this.renderFeeds();
    } catch(e) {
      console.error(e);
      if(window.showErrorToast) window.showErrorToast('Failed to load cameras for live view');
    }
  },
  
  setGrid(size) {
    this._gridSize = size;
    const container = document.getElementById('live-feeds-container');
    if (!container) return;
    container.className = `live-grid grid-${size}`;
    this.renderFeeds();
  },
  
  focusCamera(id) {
    if (!id) return;
    this.maximizeFeed(id);
    document.getElementById('live-camera-select').value = ''; // reset
  },
  
  renderFeeds() {
    const container = document.getElementById('live-feeds-container');
    if (!container) return;
    
    let count = 4;
    if (this._gridSize === '1x1') count = 1;
    if (this._gridSize === '3x3') count = 9;
    
    const displayCams = this._cameras.slice(0, count);
    
    let html = '';
    for (let i = 0; i < count; i++) {
      const cam = displayCams[i];
      if (cam) {
        html += `
          <div class="feed-item" id="feed-${cam.id}" onclick="window.livePage.maximizeFeed('${cam.id}')">
            <img 
              src="/api/stream/${cam.id}"
              alt="${cam.name}"
              onerror="this.parentElement.innerHTML='<div class=feed-no-signal><div class=icon>📷</div><span>No Signal</span></div>'"
              loading="lazy"
            />
            <div class="feed-label">
              <span class="live-badge">LIVE</span>
              ${cam.camera_id} — ${cam.name}
            </div>
          </div>
        `;
      } else {
        html += `
          <div class="feed-item" style="border-style:dashed;">
            <div class="feed-no-signal">
              <div class="icon" style="opacity:0.2;">📷</div>
              <span style="opacity:0.5;">Unassigned</span>
            </div>
          </div>
        `;
      }
    }
    
    container.innerHTML = html;
  },
  
  maximizeFeed(id) {
    const cam = this._cameras.find(c => c.id === id);
    if (!cam) return;
    
    const content = document.getElementById('maximize-content');
    content.innerHTML = `
      <img src="/api/stream/${cam.id}" style="width:100%;height:100%;object-fit:contain;" onerror="this.outerHTML='<div class=feed-no-signal style=\\'font-size:24px\\'><div class=icon style=\\'font-size:64px\\'>📷</div><span>No Signal</span></div>'">
      <div class="feed-label" style="font-size:18px;bottom:24px;left:24px;background:rgba(0,0,0,0.8);">
        <span class="live-badge" style="font-size:14px;padding:4px 8px;">LIVE</span>
        ${cam.camera_id} — ${cam.name} (${cam.location_name || 'Unknown'})
      </div>
    `;
    document.getElementById('maximize-modal').style.display = 'flex';
    // Listen for Escape key
    this._escHandler = (e) => { if (e.key === 'Escape') this._closeMaximize(); };
    document.addEventListener('keydown', this._escHandler);
  },

  _closeMaximize(e) {
    if (e && e.target !== document.getElementById('maximize-modal')) return;
    const modal = document.getElementById('maximize-modal');
    modal.style.display = 'none';
    // Exit native fullscreen if active
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    document.removeEventListener('keydown', this._escHandler);
  },

  _toggleNativeFullscreen() {
    const modal = document.getElementById('maximize-modal');
    const btn = document.getElementById('btn-native-fullscreen');
    if (!document.fullscreenElement) {
      modal.requestFullscreen().then(() => {
        if (btn) btn.textContent = '\u22A1 Exit Full Screen';
      }).catch(err => console.warn('Fullscreen error:', err));
    } else {
      document.exitFullscreen();
      if (btn) btn.textContent = '\u26F6 Full Screen';
    }
  },
  
  destroy() {
    // stop streams by removing imgs from DOM implicitly handled on unmount
  }
};

window.livePage = livePage;

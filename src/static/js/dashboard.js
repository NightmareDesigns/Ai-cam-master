/* ── Dashboard page script ─────────────────────────────────────────────── */

let cameras = [];
let events  = [];
let vendorStreams = [];

async function loadDashboard() {
  try {
    [cameras, events] = await Promise.all([
      API.get('/api/cameras/'),
      API.get('/api/events/?limit=50'),
    ]);
  } catch (e) {
    toast('Failed to load data: ' + e.message, 'error');
    return;
  }

  renderStats();
  renderCameraGrid();
  renderEventFeed();
}

function renderStats() {
  const online = cameras.filter(c => c.is_online).length;
  const todayEvents = events.filter(e => {
    const d = new Date(e.occurred_at);
    const now = new Date();
    return d.toDateString() === now.toDateString();
  });
  const persons = events.filter(e => e.object_class === 'person').length;

  document.getElementById('stat-cameras').textContent = cameras.length;
  document.getElementById('stat-online').textContent = online;
  document.getElementById('stat-events').textContent = todayEvents.length;
  document.getElementById('stat-persons').textContent = persons;
}

function renderCameraGrid() {
  const grid = document.getElementById('camera-grid');
  if (!grid) return;

  if (cameras.length === 0) {
    grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:60px;color:var(--text-muted)">
      <div style="font-size:2.5rem;margin-bottom:12px">📷</div>
      <div>No cameras added yet. <a href="/cameras">Add a camera</a> to get started.</div>
    </div>`;
    return;
  }

  grid.innerHTML = cameras.map(cam => `
    <div class="camera-tile">
      <img
        id="cam-img-${cam.id}"
        src="/snapshot/${cam.id}"
        alt="${cam.name}"
        onerror="this.src='/static/img/offline.svg'"
        loading="lazy"
      />
      <div class="cam-footer">
        <span class="cam-name">
          <span class="status-dot ${cam.is_online ? 'online' : 'offline'}"></span>
          ${cam.name}
        </span>
        <div class="cam-badges">
          ${cam.detect_objects ? badgeHtml('AI', 'accent') : ''}
          ${cam.detect_motion  ? badgeHtml('Motion', 'warning') : ''}
          ${cam.is_online ? badgeHtml('Live', 'success') : badgeHtml('Offline', 'danger')}
        </div>
      </div>
    </div>
  `).join('');

  // Refresh snapshots every 2 s
  cameras.filter(c => c.is_online).forEach(cam => {
    setInterval(() => {
      const img = document.getElementById(`cam-img-${cam.id}`);
      if (img) img.src = `/snapshot/${cam.id}?t=${Date.now()}`;
    }, 2000);
  });
}

function renderEventFeed() {
  const tbody = document.getElementById('event-tbody');
  if (!tbody) return;

  if (events.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:30px">No events yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = events.slice(0, 20).map(ev => {
    const cam = cameras.find(c => c.id === ev.camera_id);
    const typeBadge = ev.event_type === 'object_detected'
      ? badgeHtml(ev.object_class || 'object', 'accent')
      : ev.event_type === 'motion'
        ? badgeHtml('Motion', 'warning')
        : badgeHtml(ev.event_type, 'danger');

    const snap = ev.snapshot_path
      ? `<a href="/snapshots/file/${ev.snapshot_path}" target="_blank">
           <img src="/snapshots/file/${ev.snapshot_path}" style="width:60px;height:38px;object-fit:cover;border-radius:4px;"/>
         </a>`
      : '—';

    return `<tr>
      <td>${snap}</td>
      <td>${cam ? cam.name : `Cam ${ev.camera_id}`}</td>
      <td>${typeBadge}</td>
      <td>${formatConfidence(ev.confidence)}</td>
      <td style="color:var(--text-muted)">${timeSince(ev.occurred_at)}</td>
    </tr>`;
  }).join('');
}

function renderVendorStreams() {
  const container = document.getElementById('vendor-results');
  if (!container) return;
  if (!vendorStreams.length) {
    container.innerHTML = '<div class="discovery-empty">Log in above to see vendor streams.</div>';
    return;
  }
  container.innerHTML = vendorStreams.map((stream, idx) => `
    <div class="discovery-card">
      <div class="discovery-main">
        <div class="discovery-label">${stream.label || 'Vendor stream'}</div>
        <div class="discovery-source">${stream.source || '—'}</div>
      </div>
      <div class="discovery-actions">
        <button class="btn btn-primary btn-sm" onclick="saveVendorCamera(${idx})">Save camera</button>
        <button class="btn btn-ghost btn-sm" onclick="copyVendorSource(${idx})">Copy URL</button>
      </div>
    </div>
  `).join('');
}

async function saveVendorCamera(idx) {
  const stream = vendorStreams[idx];
  if (!stream || !stream.source) {
    toast('No stream URL to save.', 'error');
    return;
  }
  const body = {
    name: stream.label || 'Vendor stream',
    source: stream.source,
    location_name: stream.type || null,
    detect_objects: true,
    detect_motion: true,
    record_on_event: true,
    enabled: true,
  };
  try {
    await API.post('/api/cameras/', body);
    toast('Camera saved from vendor stream.', 'success');
    loadDashboard();
  } catch (e) {
    toast('Unable to save camera: ' + e.message, 'error');
  }
}

function copyVendorSource(idx) {
  const stream = vendorStreams[idx];
  if (!stream?.source) return;
  navigator.clipboard?.writeText(stream.source)
    .then(() => toast('Copied stream URL.', 'success'))
    .catch(() => toast('Copy failed. Select and copy manually.', 'error'));
}

document.addEventListener('DOMContentLoaded', () => {
  loadDashboard();
  setInterval(loadDashboard, 10000); // refresh every 10s

  initVendorLogins({
    zmodo: {
      host: '#zmodo-host-main',
      user: '#zmodo-user-main',
      pass: '#zmodo-pass-main',
      port: '#zmodo-port-main',
      channel: '#zmodo-channel-main',
      transport: '#zmodo-transport-main',
      httpPort: '#zmodo-http-port-main',
      snapshot: '#zmodo-snapshot-main',
      status: '#zmodo-status-main',
      button: '#btn-zmodo-login-main',
    },
    blink: {
      user: '#blink-user-main',
      pass: '#blink-pass-main',
      otp: '#blink-otp-main',
      recovery: '#blink-recovery-main',
      status: '#blink-status-main',
      button: '#btn-blink-login-main',
    },
    geeni: {
      camera: {
        host: '#geeni-host-main',
        user: '#geeni-user-main',
        pass: '#geeni-pass-main',
        port: '#geeni-port-main',
        httpPort: '#geeni-http-port-main',
        path: '#geeni-path-main',
        snapshot: '#geeni-snapshot-main',
        status: '#geeni-status-main',
        button: '#btn-geeni-login-main',
      },
      light: {
        deviceId: '#geeni-light-id-main',
        localKey: '#geeni-light-key-main',
        ip: '#geeni-light-ip-main',
        state: '#geeni-light-state-main',
        brightness: '#geeni-light-brightness-main',
        protocol: '#geeni-light-protocol-main',
        status: '#geeni-light-status-main',
        button: '#btn-geeni-light-main',
      },
    },
    eesee: {
      host: '#eesee-host-main',
      user: '#eesee-user-main',
      pass: '#eesee-pass-main',
      port: '#eesee-port-main',
      channel: '#eesee-channel-main',
      subtype: '#eesee-subtype-main',
      path: '#eesee-path-main',
      snapshotPath: '#eesee-snapshot-path-main',
      httpPort: '#eesee-http-port-main',
      snapshotMode: '#eesee-snapshot-main',
      status: '#eesee-status-main',
      button: '#btn-eesee-login-main',
    },
    onResults: streams => {
      vendorStreams = Array.isArray(streams) ? streams : [];
      renderVendorStreams();
    },
    onError: (vendor, msg) => {
      const name = vendor === 'zmodo'
        ? 'Zmodo'
        : vendor === 'blink'
          ? 'Blink'
          : vendor === 'geeni' || vendor === 'geeniLight'
            ? 'Geeni'
            : 'EseeCam';
      toast(`${name} login failed: ${msg}`, 'error');
    },
    onSuccess: (vendor, msg) => {
      const name = vendor === 'zmodo'
        ? 'Zmodo'
        : vendor === 'blink'
          ? 'Blink'
          : vendor === 'geeni' || vendor === 'geeniLight'
            ? 'Geeni'
            : 'EseeCam';
      toast(`${name}: ${msg}`, 'success');
    },
  });
  renderVendorStreams();
});

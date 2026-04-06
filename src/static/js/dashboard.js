/* ── Dashboard page script ─────────────────────────────────────────────── */

let cameras = [];
let events  = [];

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

document.addEventListener('DOMContentLoaded', () => {
  loadDashboard();
  setInterval(loadDashboard, 10000); // refresh every 10s
});

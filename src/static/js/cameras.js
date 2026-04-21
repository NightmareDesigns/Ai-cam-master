/* ── Cameras management page ───────────────────────────────────────────── */

let cameras = [];
let discoveries = [];
let discovering = false;
async function loadCameras() {
  try {
    cameras = await API.get('/api/cameras/');
  } catch (e) {
    toast('Failed to load cameras: ' + e.message, 'error');
    return;
  }
  renderTable();
}

function renderTable() {
  const tbody = document.getElementById('cameras-tbody');
  if (!tbody) return;

  if (cameras.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:30px;color:var(--text-muted)">
      No cameras. Click "Add Camera" to add one.
    </td></tr>`;
    return;
  }

  tbody.innerHTML = cameras.map(cam => `
    <tr>
      <td>
        <span class="status-dot ${cam.is_online ? 'online' : 'offline'}"></span>
        ${cam.name}
      </td>
      <td style="font-family:monospace;font-size:.8rem;color:var(--text-muted)">${cam.source}</td>
      <td>${cam.detect_objects ? badgeHtml('On','success') : badgeHtml('Off','danger')}</td>
      <td>${cam.detect_motion ? badgeHtml('On','success') : badgeHtml('Off','danger')}</td>
      <td>${cam.is_online ? badgeHtml('Online','success') : badgeHtml('Offline','danger')}</td>
      <td>
        <button class="btn btn-ghost btn-sm" onclick="openEdit(${cam.id})">Edit</button>
        <button class="btn btn-danger btn-sm" onclick="deleteCamera(${cam.id})">Delete</button>
        ${cam.is_online
          ? `<a class="btn btn-accent btn-sm" href="/stream/${cam.id}" target="_blank"
               style="background:var(--accent);color:#fff">▶ Live</a>`
          : ''}
      </td>
    </tr>
  `).join('');
}

/* ── Add camera ────────────────────────────────────────────────────────── */
function openAdd() {
  document.getElementById('modal-title').textContent = 'Add Camera';
  document.getElementById('cam-id').value = '';
  document.getElementById('cam-name').value = '';
  document.getElementById('cam-source').value = '';
  document.getElementById('cam-location').value = '';
  document.getElementById('cam-detect-objects').checked = true;
  document.getElementById('cam-detect-motion').checked = true;
  document.getElementById('cam-record').checked = true;
  document.getElementById('cam-enabled').checked = true;
  document.getElementById('camera-modal').classList.add('open');
}

function openEdit(id) {
  const cam = cameras.find(c => c.id === id);
  if (!cam) return;
  document.getElementById('modal-title').textContent = 'Edit Camera';
  document.getElementById('cam-id').value = cam.id;
  document.getElementById('cam-name').value = cam.name;
  document.getElementById('cam-source').value = cam.source;
  document.getElementById('cam-location').value = cam.location_name || '';
  document.getElementById('cam-detect-objects').checked = cam.detect_objects;
  document.getElementById('cam-detect-motion').checked = cam.detect_motion;
  document.getElementById('cam-record').checked = cam.record_on_event;
  document.getElementById('cam-enabled').checked = cam.enabled;
  document.getElementById('camera-modal').classList.add('open');
}

function closeModal() {
  document.getElementById('camera-modal').classList.remove('open');
}

async function saveCamera() {
  const id = document.getElementById('cam-id').value;
  const body = {
    name: document.getElementById('cam-name').value.trim(),
    source: document.getElementById('cam-source').value.trim(),
    location_name: document.getElementById('cam-location').value.trim() || null,
    detect_objects: document.getElementById('cam-detect-objects').checked,
    detect_motion: document.getElementById('cam-detect-motion').checked,
    record_on_event: document.getElementById('cam-record').checked,
    enabled: document.getElementById('cam-enabled').checked,
  };

  if (!body.name || !body.source) {
    toast('Name and source are required.', 'error');
    return;
  }

  try {
    if (id) {
      await API.patch(`/api/cameras/${id}`, body);
      toast('Camera updated.', 'success');
    } else {
      await API.post('/api/cameras/', body);
      toast('Camera added.', 'success');
    }
    closeModal();
    loadCameras();
  } catch (e) {
    toast('Error: ' + e.message, 'error');
  }
}

async function deleteCamera(id) {
  if (!confirm('Delete this camera and all its events?')) return;
  try {
    await API.del(`/api/cameras/${id}`);
    toast('Camera deleted.', 'success');
    loadCameras();
  } catch (e) {
    toast('Error: ' + e.message, 'error');
  }
}

/* ── Auto-discovery ────────────────────────────────────────────────────── */
function renderDiscoveryResults() {
  const container = document.getElementById('discover-results');
  if (!container) return;
  if (!discoveries.length) {
    container.innerHTML = '<div class="discovery-empty">No results yet. Start a scan to see nearby cameras.</div>';
    return;
  }
  container.innerHTML = discoveries
    .map((d, idx) => `
      <div class="discovery-card">
        <div class="discovery-main">
          <div class="discovery-label">${d.label}</div>
          <div class="discovery-meta">
            <span class="badge badge-accent">${d.type.toUpperCase()}</span>
            ${d.port ? `<span class="badge badge-warning">:${d.port}</span>` : ''}
          </div>
          <div class="discovery-source">${d.source}</div>
          ${d.evidence ? `<div class="text-muted" style="font-size:.8rem">${d.evidence}</div>` : ''}
        </div>
        <div class="discovery-actions">
          <button class="btn btn-primary btn-sm" onclick="addDiscovery(${idx})">Add</button>
        </div>
      </div>
    `)
    .join('');
}

function mergeDiscoveries(newOnes = []) {
  const seen = new Set(discoveries.map(d => d.source));
  newOnes.forEach(d => {
    if (!d || !d.source || seen.has(d.source)) return;
    discoveries.push(d);
    seen.add(d.source);
  });
  renderDiscoveryResults();
}

function openDiscover() {
  discoveries = [];
  renderDiscoveryResults();
  setDiscoveryStatus('Ready to scan.');
  const zmodoStatus = document.getElementById('zmodo-status');
  const blinkStatus = document.getElementById('blink-status');
  if (zmodoStatus) zmodoStatus.textContent = 'Ready.';
  if (blinkStatus) blinkStatus.textContent = 'Ready.';
  const modal = document.getElementById('discovery-modal');
  if (modal) modal.classList.add('open');
}

function closeDiscover() {
  const modal = document.getElementById('discovery-modal');
  if (modal) modal.classList.remove('open');
}

function setDiscoveryStatus(text) {
  const el = document.getElementById('discover-status');
  if (el) el.textContent = text;
}

async function runDiscovery() {
  if (discovering) return;
  discovering = true;
  setDiscoveryStatus('Scanning…');
  const subnetsInput = document.getElementById('discover-subnets')?.value || '';
  const subnets = subnetsInput
    .split(/[,\n\s]+/)
    .map(s => s.trim())
    .filter(Boolean);
  const body = {
    include_usb: document.getElementById('discover-include-usb')?.checked ?? true,
    timeout_seconds: parseFloat(document.getElementById('discover-timeout')?.value || '0.75') || 0.75,
    max_results: parseInt(document.getElementById('discover-max-results')?.value || '25', 10) || 25,
    max_hosts: parseInt(document.getElementById('discover-max-hosts')?.value || '256', 10) || 256,
  };
  if (subnets.length) body.subnets = subnets;
  try {
    discoveries = await API.post('/api/cameras/discover', body);
    renderDiscoveryResults();
    setDiscoveryStatus(`Found ${discoveries.length} potential camera${discoveries.length === 1 ? '' : 's'}.`);
  } catch (e) {
    toast('Discovery failed: ' + e.message, 'error');
    setDiscoveryStatus('Discovery failed. Adjust subnets or timeout and retry.');
  } finally {
    discovering = false;
  }
}

function addDiscovery(idx) {
  const d = discoveries[idx];
  if (!d) return;
  openAdd();
  document.getElementById('cam-name').value = d.label || 'Auto-discovered camera';
  document.getElementById('cam-source').value = d.source;
  document.getElementById('cam-detect-objects').checked = true;
  document.getElementById('cam-detect-motion').checked = true;
}

document.addEventListener('DOMContentLoaded', () => {
  loadCameras();
  document.getElementById('btn-add-camera').addEventListener('click', openAdd);
  document.getElementById('btn-cancel').addEventListener('click', closeModal);
  document.getElementById('btn-save').addEventListener('click', saveCamera);
  document.getElementById('btn-discover').addEventListener('click', openDiscover);
  document.getElementById('btn-close-discover').addEventListener('click', closeDiscover);
  document.getElementById('btn-run-discover').addEventListener('click', runDiscovery);

  initVendorLogins({
    zmodo: {
      host: '#zmodo-host',
      user: '#zmodo-user',
      pass: '#zmodo-pass',
      port: '#zmodo-port',
      channel: '#zmodo-channel',
      transport: '#zmodo-transport',
      httpPort: '#zmodo-http-port',
      snapshot: '#zmodo-snapshot',
      status: '#zmodo-status',
      button: '#btn-zmodo-login',
    },
    blink: {
      user: '#blink-user',
      pass: '#blink-pass',
      otp: '#blink-otp',
      status: '#blink-status',
      button: '#btn-blink-login',
    },
    geeni: {
      camera: {
        host: '#geeni-host',
        user: '#geeni-user',
        pass: '#geeni-pass',
        port: '#geeni-port',
        httpPort: '#geeni-http-port',
        path: '#geeni-path',
        snapshot: '#geeni-snapshot',
        status: '#geeni-status',
        button: '#btn-geeni-login',
      },
      light: {
        deviceId: '#geeni-light-id',
        localKey: '#geeni-light-key',
        ip: '#geeni-light-ip',
        state: '#geeni-light-state',
        brightness: '#geeni-light-brightness',
        protocol: '#geeni-light-protocol',
        status: '#geeni-light-status',
        button: '#btn-geeni-light',
      },
    },
    onResults: streams => {
      if (Array.isArray(streams)) mergeDiscoveries(streams);
    },
    onError: (vendor, msg) => {
      const name = vendor === 'zmodo' ? 'Zmodo' : vendor === 'blink' ? 'Blink' : 'Geeni';
      toast(`${name} login failed: ${msg}`, 'error');
    },
  });
});

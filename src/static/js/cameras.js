/* ── Cameras management page ───────────────────────────────────────────── */

let cameras = [];

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

document.addEventListener('DOMContentLoaded', () => {
  loadCameras();
  document.getElementById('btn-add-camera').addEventListener('click', openAdd);
  document.getElementById('btn-cancel').addEventListener('click', closeModal);
  document.getElementById('btn-save').addEventListener('click', saveCamera);
});

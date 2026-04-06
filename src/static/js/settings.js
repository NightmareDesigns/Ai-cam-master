/* ── Settings / Alert rules page ───────────────────────────────────────── */

let rules = [];
let cameras = [];

async function loadData() {
  try {
    [rules, cameras] = await Promise.all([
      API.get('/api/alerts/'),
      API.get('/api/cameras/'),
    ]);
  } catch (e) {
    toast('Failed to load settings: ' + e.message, 'error');
    return;
  }
  renderRules();
}

function renderRules() {
  const tbody = document.getElementById('rules-tbody');
  if (!tbody) return;

  if (rules.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:30px;color:var(--text-muted)">
      No alert rules. Click "Add Rule" to create one.
    </td></tr>`;
    return;
  }

  tbody.innerHTML = rules.map(r => {
    const cam = r.camera_id ? cameras.find(c => c.id === r.camera_id) : null;
    return `<tr>
      <td>${r.name}</td>
      <td>${r.camera_id ? (cam ? cam.name : `Cam ${r.camera_id}`) : '<em style="color:var(--text-muted)">All cameras</em>'}</td>
      <td><code>${r.trigger_class}</code></td>
      <td>${r.notify_via}</td>
      <td>${r.enabled ? badgeHtml('Enabled','success') : badgeHtml('Disabled','danger')}</td>
      <td>
        <button class="btn btn-ghost btn-sm" onclick="openEdit(${r.id})">Edit</button>
        <button class="btn btn-danger btn-sm" onclick="deleteRule(${r.id})">Delete</button>
      </td>
    </tr>`;
  }).join('');
}

function openAdd() {
  document.getElementById('modal-title').textContent = 'Add Alert Rule';
  document.getElementById('rule-id').value = '';
  document.getElementById('rule-name').value = '';
  document.getElementById('rule-trigger').value = '*';
  document.getElementById('rule-notify').value = 'console';
  document.getElementById('rule-webhook').value = '';
  document.getElementById('rule-enabled').checked = true;
  populateCameraSelect(null);
  document.getElementById('rule-modal').classList.add('open');
}

function openEdit(id) {
  const r = rules.find(x => x.id === id);
  if (!r) return;
  document.getElementById('modal-title').textContent = 'Edit Alert Rule';
  document.getElementById('rule-id').value = r.id;
  document.getElementById('rule-name').value = r.name;
  document.getElementById('rule-trigger').value = r.trigger_class;
  document.getElementById('rule-notify').value = r.notify_via;
  document.getElementById('rule-webhook').value = r.webhook_url || '';
  document.getElementById('rule-enabled').checked = r.enabled;
  populateCameraSelect(r.camera_id);
  document.getElementById('rule-modal').classList.add('open');
}

function populateCameraSelect(selectedId) {
  const sel = document.getElementById('rule-camera');
  sel.innerHTML = '<option value="">All cameras</option>';
  cameras.forEach(c => {
    const o = document.createElement('option');
    o.value = c.id; o.textContent = c.name;
    if (c.id === selectedId) o.selected = true;
    sel.appendChild(o);
  });
}

function closeModal() {
  document.getElementById('rule-modal').classList.remove('open');
}

async function saveRule() {
  const id = document.getElementById('rule-id').value;
  const camVal = document.getElementById('rule-camera').value;
  const body = {
    name: document.getElementById('rule-name').value.trim(),
    trigger_class: document.getElementById('rule-trigger').value.trim() || '*',
    notify_via: document.getElementById('rule-notify').value.trim() || 'console',
    webhook_url: document.getElementById('rule-webhook').value.trim() || null,
    enabled: document.getElementById('rule-enabled').checked,
    camera_id: camVal ? parseInt(camVal) : null,
  };

  if (!body.name) { toast('Name is required.', 'error'); return; }

  try {
    if (id) {
      await API.patch(`/api/alerts/${id}`, body);
      toast('Alert rule updated.', 'success');
    } else {
      await API.post('/api/alerts/', body);
      toast('Alert rule created.', 'success');
    }
    closeModal();
    loadData();
  } catch (e) {
    toast('Error: ' + e.message, 'error');
  }
}

async function deleteRule(id) {
  if (!confirm('Delete this alert rule?')) return;
  try {
    await API.del(`/api/alerts/${id}`);
    toast('Rule deleted.', 'success');
    loadData();
  } catch (e) {
    toast('Error: ' + e.message, 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadData();
  document.getElementById('btn-add-rule').addEventListener('click', openAdd);
  document.getElementById('btn-cancel').addEventListener('click', closeModal);
  document.getElementById('btn-save').addEventListener('click', saveRule);
});

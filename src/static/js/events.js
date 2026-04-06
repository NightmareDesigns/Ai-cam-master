/* ── Events page script ────────────────────────────────────────────────── */

let cameras = [];
let events = [];
let page = 0;
const PAGE_SIZE = 50;

async function loadData() {
  try {
    cameras = await API.get('/api/cameras/');
  } catch (e) { /* not critical */ }
  await loadEvents();
}

async function loadEvents(reset = true) {
  if (reset) { page = 0; events = []; }

  const camId = document.getElementById('filter-camera').value;
  const evType = document.getElementById('filter-type').value;
  const objClass = document.getElementById('filter-class').value;

  let url = `/api/events/?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`;
  if (camId)   url += `&camera_id=${camId}`;
  if (evType)  url += `&event_type=${evType}`;
  if (objClass) url += `&object_class=${objClass}`;

  try {
    const batch = await API.get(url);
    events = reset ? batch : [...events, ...batch];
    renderTable();
    document.getElementById('btn-load-more').style.display =
      batch.length === PAGE_SIZE ? 'inline-flex' : 'none';
  } catch (e) {
    toast('Failed to load events: ' + e.message, 'error');
  }
}

function renderTable() {
  const tbody = document.getElementById('events-tbody');
  if (!tbody) return;

  // Populate camera filter options once
  const sel = document.getElementById('filter-camera');
  if (sel.options.length === 1 && cameras.length > 0) {
    cameras.forEach(c => {
      const o = document.createElement('option');
      o.value = c.id; o.textContent = c.name;
      sel.appendChild(o);
    });
  }

  if (events.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:30px;color:var(--text-muted)">
      No events found.
    </td></tr>`;
    return;
  }

  tbody.innerHTML = events.map(ev => {
    const cam = cameras.find(c => c.id === ev.camera_id);
    const typeBadge = ev.event_type === 'object_detected'
      ? badgeHtml(ev.object_class || 'object', 'accent')
      : ev.event_type === 'motion'
        ? badgeHtml('Motion', 'warning')
        : badgeHtml(ev.event_type, 'danger');

    const snap = ev.snapshot_path
      ? `<a href="/snapshots/file/${ev.snapshot_path}" target="_blank">
           <img src="/snapshots/file/${ev.snapshot_path}"
                style="width:72px;height:45px;object-fit:cover;border-radius:5px;"/>
         </a>`
      : '<span style="color:var(--text-muted)">—</span>';

    return `<tr>
      <td>${snap}</td>
      <td>${cam ? cam.name : `Cam ${ev.camera_id}`}</td>
      <td>${typeBadge}</td>
      <td>${formatConfidence(ev.confidence)}</td>
      <td style="color:var(--text-muted);font-size:.8rem">
        ${new Date(ev.occurred_at).toLocaleString()}
      </td>
      <td>
        ${ev.snapshot_path
          ? `<a class="btn btn-ghost btn-sm"
               href="/snapshots/file/${ev.snapshot_path}" target="_blank">View</a>`
          : ''}
      </td>
    </tr>`;
  }).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  loadData();
  document.getElementById('filter-camera').addEventListener('change', () => loadEvents(true));
  document.getElementById('filter-type').addEventListener('change', () => loadEvents(true));
  document.getElementById('filter-class').addEventListener('change', () => loadEvents(true));
  document.getElementById('btn-load-more').addEventListener('click', () => {
    page++;
    loadEvents(false);
  });
});

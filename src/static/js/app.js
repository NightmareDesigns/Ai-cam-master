/* ── App.js — shared utilities ─────────────────────────────────────────── */

const API = {
  async get(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`GET ${url} → ${r.status}`);
    return r.json();
  },
  async post(url, body) {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`POST ${url} → ${r.status}: ${await r.text()}`);
    return r.json();
  },
  async patch(url, body) {
    const r = await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`PATCH ${url} → ${r.status}: ${await r.text()}`);
    return r.json();
  },
  async del(url) {
    const r = await fetch(url, { method: 'DELETE' });
    if (!r.ok && r.status !== 204) throw new Error(`DELETE ${url} → ${r.status}`);
    return r.status === 204 ? null : r.json();
  },
};

function toast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

function timeSince(dateStr) {
  const d = new Date(dateStr);
  const secs = Math.floor((Date.now() - d.getTime()) / 1000);
  if (secs < 60)    return `${secs}s ago`;
  if (secs < 3600)  return `${Math.floor(secs/60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs/3600)}h ago`;
  return d.toLocaleDateString();
}

function formatConfidence(conf) {
  if (conf == null) return '—';
  return (conf * 100).toFixed(0) + '%';
}

function badgeHtml(label, type = 'accent') {
  return `<span class="badge badge-${type}">${label}</span>`;
}

function initMatrixRain() {
  const canvas = document.getElementById('matrix-bg');
  if (!canvas || !canvas.getContext) return;
  const ctx = canvas.getContext('2d');
  let width = canvas.width = window.innerWidth;
  let height = canvas.height = window.innerHeight;
  const chars = '01░▒▓█ACEGHKMNRSTVXZ';
  let drops = Array(Math.floor(width / 18)).fill(1);

  function resize() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    drops = Array(Math.floor(width / 18)).fill(1);
  }
  window.addEventListener('resize', resize);

  function draw() {
    ctx.fillStyle = 'rgba(0,0,0,0.15)';
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = '#39ff14';
    ctx.shadowColor = 'rgba(57,255,20,0.35)';
    ctx.shadowBlur = 6;
    ctx.font = '16px "Share Tech Mono", monospace';

    drops.forEach((drop, i) => {
      const text = chars[Math.floor(Math.random() * chars.length)];
      ctx.fillText(text, i * 18, drop * 18);
      if (drop * 18 > height && Math.random() > 0.965) drops[i] = 0;
      drops[i] = drops[i] + 1;
    });
    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);
}

/* Highlight the active nav item */
document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname.replace(/\/$/, '') || '/';
  document.querySelectorAll('.sidebar-nav a').forEach(a => {
    const href = a.getAttribute('href').replace(/\/$/, '') || '/';
    if (href === path) a.classList.add('active');
  });
  initMatrixRain();
});

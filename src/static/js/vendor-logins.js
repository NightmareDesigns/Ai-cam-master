/* ── Shared vendor login helpers (Zmodo + Blink) ─────────────────────── */

function initVendorLogins(config = {}) {
  const busy = { zmodo: false, blink: false };
  const { zmodo = {}, blink = {}, onResults, onError, onSuccess, onStatus } = config;

  const notify = (msg, type = 'info') => {
    if (typeof toast === 'function') toast(msg, type);
    else console.info(type.toUpperCase(), msg);
  };

  const getEl = ref => (typeof ref === 'string' ? document.querySelector(ref) : ref) || null;
  const getVal = ref => getEl(ref)?.value?.trim();
  const setStatus = (vendor, text) => {
    const statusEl = vendor === 'zmodo' ? getEl(zmodo.status) : getEl(blink.status);
    if (statusEl) statusEl.textContent = text;
    if (typeof onStatus === 'function') onStatus(vendor, text);
  };

  async function loginZmodo() {
    if (busy.zmodo) return;
    const host = getVal(zmodo.host);
    const user = getVal(zmodo.user);
    const pass = getEl(zmodo.pass)?.value ?? '';
    const port = parseInt(getVal(zmodo.port) || '10554', 10) || 10554;
    const channel = parseInt(getVal(zmodo.channel) || '0', 10) || 0;
    const transport = getVal(zmodo.transport) || 'tcp';

    if (!host || !user || !pass) {
      notify('Zmodo host, user, and password are required.', 'error');
      return;
    }

    busy.zmodo = true;
    setStatus('zmodo', 'Contacting Zmodo…');
    const body = { host, username: user, password: pass, port, channel, transport };

    try {
      const res = await API.post('/api/cameras/zmodo/login', body);
      if (onResults) onResults(res || []);
      const label = res?.length
        ? `Added ${res.length} stream${res.length === 1 ? '' : 's'}.`
        : 'No streams returned.';
      setStatus('zmodo', label);
      if (onSuccess) onSuccess('zmodo', label);
    } catch (e) {
      setStatus('zmodo', 'Login failed. Check credentials/IP and retry.');
      if (onError) onError('zmodo', e.message || 'Login failed');
      else notify('Zmodo login failed: ' + e.message, 'error');
    } finally {
      busy.zmodo = false;
    }
  }

  async function loginBlink() {
    if (busy.blink) return;
    const username = getVal(blink.user);
    const password = getEl(blink.pass)?.value ?? '';
    const twofa = getVal(blink.otp) || null;

    if (!username || !password) {
      notify('Blink email and password are required.', 'error');
      return;
    }

    busy.blink = true;
    setStatus('blink', 'Logging in to Blink…');
    const body = { username, password };
    if (twofa) body.two_factor_code = twofa;

    try {
      const res = await API.post('/api/cameras/blink/login', body);
      if (onResults) onResults(res || []);
      const label = res?.length
        ? `Fetched ${res.length} Blink camera${res.length === 1 ? '' : 's'}.`
        : 'No Blink cameras returned.';
      setStatus('blink', label);
      if (onSuccess) onSuccess('blink', label);
    } catch (e) {
      setStatus('blink', 'Login failed. Check credentials/2FA.');
      if (onError) onError('blink', e.message || 'Login failed');
      else notify('Blink login failed: ' + e.message, 'error');
    } finally {
      busy.blink = false;
    }
  }

  const zButton = getEl(zmodo.button);
  const bButton = getEl(blink.button);
  if (zButton) zButton.addEventListener('click', loginZmodo);
  if (bButton) bButton.addEventListener('click', loginBlink);

  // Initialize statuses to Ready when present
  if (getEl(zmodo.status)) setStatus('zmodo', 'Ready.');
  if (getEl(blink.status)) setStatus('blink', 'Ready.');

  return { loginZmodo, loginBlink };
}

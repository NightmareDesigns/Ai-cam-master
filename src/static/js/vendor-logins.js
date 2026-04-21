/* ── Shared vendor login helpers (Zmodo + Blink + Geeni) ─────────────── */

function initVendorLogins(config = {}) {
  const busy = { zmodo: false, blink: false, geeni: false, geeniLight: false, eesee: false };
  const { zmodo = {}, blink = {}, geeni = {}, eesee = {}, onResults, onError, onSuccess, onStatus } = config;
  const geeniCam = geeni.camera || {};
  const geeniLight = geeni.light || {};

  const notify = (msg, type = 'info') => {
    if (typeof toast === 'function') toast(msg, type);
    else console.info(type.toUpperCase(), msg);
  };

  const getEl = ref => (typeof ref === 'string' ? document.querySelector(ref) : ref) || null;
  const getVal = ref => getEl(ref)?.value?.trim();
  const setStatus = (vendor, text) => {
    let statusEl = null;
    if (vendor === 'zmodo') statusEl = getEl(zmodo.status);
    else if (vendor === 'blink') statusEl = getEl(blink.status);
    else if (vendor === 'geeni') statusEl = getEl(geeniCam.status);
    else if (vendor === 'geeniLight') statusEl = getEl(geeniLight.status);
    else if (vendor === 'eesee') statusEl = getEl(eesee.status);
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
    const httpPort = parseInt(getVal(zmodo.httpPort) || '80', 10) || 80;
    const preferSnapshot = Boolean(getEl(zmodo.snapshot)?.checked);

    if (!host || !user || !pass) {
      notify('Zmodo host, user, and password are required.', 'error');
      return;
    }

    busy.zmodo = true;
    setStatus('zmodo', 'Contacting Zmodo…');
    const body = {
      host,
      username: user,
      password: pass,
      port,
      channel,
      transport,
      http_port: httpPort,
      mode: preferSnapshot ? 'jpeg' : 'rtsp',
      fallback_to_snapshot: true,
    };

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
    const recovery = getVal(blink.recovery) || null;

    if (!username || !password) {
      notify('Blink email and password are required.', 'error');
      return;
    }

    busy.blink = true;
    setStatus('blink', 'Logging in to Blink…');
    const body = { username, password };
    if (twofa) body.two_factor_code = twofa;
    if (recovery) body.two_factor_recovery_code = recovery;

    try {
      const res = await API.post('/api/cameras/blink/login', body);
      if (onResults) onResults(res || []);
      const label = res?.length
        ? `Fetched ${res.length} Blink camera${res.length === 1 ? '' : 's'}.`
        : 'No Blink cameras returned.';
      setStatus('blink', label);
      if (onSuccess) onSuccess('blink', label);
    } catch (e) {
      setStatus('blink', 'Login failed. Check credentials/2FA/recovery code.');
      if (onError) onError('blink', e.message || 'Login failed');
      else notify('Blink login failed: ' + e.message, 'error');
    } finally {
      busy.blink = false;
    }
  }

  async function loginGeeniCamera() {
    if (busy.geeni) return;
    const host = getVal(geeniCam.host);
    const user = getVal(geeniCam.user) || 'admin';
    const pass = getEl(geeniCam.pass)?.value ?? '';
    const port = parseInt(getVal(geeniCam.port) || '554', 10) || 554;
    const httpPort = parseInt(getVal(geeniCam.httpPort) || '80', 10) || 80;
    const streamPath = getVal(geeniCam.path) || 'live/main';
    const preferSnapshot = Boolean(getEl(geeniCam.snapshot)?.checked);

    if (!host) {
      notify('Geeni host/IP is required.', 'error');
      return;
    }

    busy.geeni = true;
    setStatus('geeni', 'Contacting Geeni…');
    const body = {
      host,
      username: user,
      password: pass,
      port,
      stream_path: streamPath,
      http_port: httpPort,
      mode: preferSnapshot ? 'jpeg' : 'rtsp',
      fallback_to_snapshot: true,
    };

    try {
      const res = await API.post('/api/geeni/cameras/login', body);
      if (onResults) onResults(res || []);
      const label = res?.length
        ? `Added ${res.length} Geeni stream${res.length === 1 ? '' : 's'}.`
        : 'No Geeni streams returned.';
      setStatus('geeni', label);
      if (onSuccess) onSuccess('geeni', label);
    } catch (e) {
      setStatus('geeni', 'Login failed. Check IP/credentials and retry.');
      if (onError) onError('geeni', e.message || 'Login failed');
      else notify('Geeni login failed: ' + e.message, 'error');
    } finally {
      busy.geeni = false;
    }
  }

  async function loginEseeCam() {
    if (busy.eesee) return;
    const host = getVal(eesee.host);
    const user = getVal(eesee.user) || 'admin';
    const pass = getEl(eesee.pass)?.value ?? '';
    const port = parseInt(getVal(eesee.port) || '554', 10) || 554;
    const channel = parseInt(getVal(eesee.channel) || '1', 10) || 1;
    const subtype = parseInt(getVal(eesee.subtype) || '0', 10);
    const streamPath = getVal(eesee.path) || 'cam/realmonitor';
    const snapshotPath = getVal(eesee.snapshotPath) || '/webcapture.jpg?command=snap&channel={channel}';
    const httpPort = parseInt(getVal(eesee.httpPort) || '80', 10) || 80;
    const preferSnapshot = Boolean(getEl(eesee.snapshotMode)?.checked);

    if (!host) {
      notify('EseeCam host/IP is required.', 'error');
      return;
    }

    busy.eesee = true;
    setStatus('eesee', 'Contacting EseeCam…');
    const body = {
      host,
      username: user,
      password: pass,
      port,
      channel,
      subtype: Number.isInteger(subtype) ? subtype : 0,
      stream_path: streamPath,
      snapshot_path: snapshotPath,
      http_port: httpPort,
      mode: preferSnapshot ? 'jpeg' : 'rtsp',
      fallback_to_snapshot: true,
    };

    try {
      const res = await API.post('/api/cameras/eeseecam/login', body);
      if (onResults) onResults(res || []);
      const label = res?.length
        ? `Added ${res.length} EseeCam stream${res.length === 1 ? '' : 's'}.`
        : 'No EseeCam streams returned.';
      setStatus('eesee', label);
      if (onSuccess) onSuccess('eesee', label);
    } catch (e) {
      setStatus('eesee', 'Login failed. Check IP/credentials and retry.');
      if (onError) onError('eesee', e.message || 'Login failed');
      else notify('EseeCam login failed: ' + e.message, 'error');
    } finally {
      busy.eesee = false;
    }
  }

  async function toggleGeeniLight() {
    if (busy.geeniLight) return;
    const deviceId = getVal(geeniLight.deviceId);
    const localKey = getVal(geeniLight.localKey);
    const ip = getVal(geeniLight.ip);
    const on = getEl(geeniLight.state)?.checked ?? true;
    const brightness = parseInt(getVal(geeniLight.brightness) || '0', 10) || null;
    const protocolVersion = getVal(geeniLight.protocol) || '3.3';

    if (!deviceId || !localKey || !ip) {
      notify('Geeni light Device ID, Local Key, and IP are required.', 'error');
      return;
    }

    busy.geeniLight = true;
    setStatus('geeniLight', 'Sending command to light…');
    const body = {
      device_id: deviceId,
      local_key: localKey,
      ip,
      state: on,
      protocol_version: protocolVersion,
    };
    if (brightness && brightness > 0) body.brightness = brightness;

    try {
      const res = await API.post('/api/geeni/lights/toggle', body);
      const label = res?.ok ? 'Light updated.' : 'Light command sent.';
      setStatus('geeniLight', label);
      if (onSuccess) onSuccess('geeniLight', label);
    } catch (e) {
      setStatus('geeniLight', 'Light command failed.');
      if (onError) onError('geeniLight', e.message || 'Command failed');
      else notify('Geeni light error: ' + e.message, 'error');
    } finally {
      busy.geeniLight = false;
    }
  }

  const zButton = getEl(zmodo.button);
  const bButton = getEl(blink.button);
  const gButton = getEl(geeniCam.button);
  const glButton = getEl(geeniLight.button);
  const eButton = getEl(eesee.button);
  if (zButton) zButton.addEventListener('click', loginZmodo);
  if (bButton) bButton.addEventListener('click', loginBlink);
  if (gButton) gButton.addEventListener('click', loginGeeniCamera);
  if (glButton) glButton.addEventListener('click', toggleGeeniLight);
  if (eButton) eButton.addEventListener('click', loginEseeCam);

  // Initialize statuses to Ready when present
  if (getEl(zmodo.status)) setStatus('zmodo', 'Ready.');
  if (getEl(blink.status)) setStatus('blink', 'Ready.');
  if (getEl(geeniCam.status)) setStatus('geeni', 'Ready.');
  if (getEl(geeniLight.status)) setStatus('geeniLight', 'Ready.');
  if (getEl(eesee.status)) setStatus('eesee', 'Ready.');

  return { loginZmodo, loginBlink, loginGeeniCamera, loginEseeCam, toggleGeeniLight };
}

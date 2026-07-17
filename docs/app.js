const $ = (id) => document.getElementById(id);
const form = $('builder');
const statusEl = $('status');
const submitBtn = $('submitBtn');

function sourceMode() { return document.querySelector('input[name="sourceMode"]:checked').value; }
document.querySelectorAll('input[name="sourceMode"]').forEach(r => r.addEventListener('change', () => {
  $('urlBox').classList.toggle('hidden', sourceMode() !== 'url');
  $('offlineBox').classList.toggle('hidden', sourceMode() !== 'offline');
}));

function safeName(v) { return v.trim().replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/^-+|-+$/g, '') || 'WebApp'; }
function requestId() { return `${Date.now()}-${crypto.randomUUID().slice(0, 8)}`; }
function setStatus(t) { statusEl.textContent = t; }

async function fileToBase64(file) {
  const buf = new Uint8Array(await file.arrayBuffer());
  let binary = '';
  const chunk = 0x8000;
  for (let i = 0; i < buf.length; i += chunk) binary += String.fromCharCode(...buf.subarray(i, i + chunk));
  return btoa(binary);
}

function collectConfig() {
  return {
    appName: $('appName').value.trim(), ipaName: safeName($('ipaName').value), bundleId: $('bundleId').value.trim(),
    version: $('version').value.trim(), build: String($('build').value), minIos: $('minIos').value.trim(),
    sourceMode: sourceMode(), websiteUrl: $('websiteUrl').value.trim(), allowHttp: $('allowHttp').checked,
    splashColor: $('splashColor').value, orientation: $('orientation').value, userAgent: $('userAgent').value.trim(),
    fullscreen: $('fullscreen').checked, backGesture: $('backGesture').checked, openExternal: $('openExternal').checked,
    preventSleep: $('preventSleep').checked, cameraText: $('cameraText').value.trim(), microphoneText: $('microphoneText').value.trim(),
    photosText: $('photosText').value.trim(), photosAddText: $('photosAddText').value.trim(), locationText: $('locationText').value.trim()
  };
}

function validateConfig(c) {
  if (!/^[A-Za-z0-9.-]+$/.test(c.bundleId) || !c.bundleId.includes('.')) throw new Error('Bundle ID 格式不正確。');
  if (c.sourceMode === 'url' && !/^https?:\/\//i.test(c.websiteUrl)) throw new Error('請輸入完整網址。');
  if (c.sourceMode === 'offline' && !$('siteZip').files[0]) throw new Error('請選擇離線網站 ZIP。');
  if (!$('icon').files[0]) throw new Error('請選擇 App 圖示。');
}

async function github(path, options = {}) {
  const owner = $('owner').value.trim(), repo = $('repo').value.trim(), token = $('token').value.trim();
  const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/${path}`, {
    ...options,
    headers: { 'Accept': 'application/vnd.github+json', 'Authorization': `Bearer ${token}`, 'X-GitHub-Api-Version': '2022-11-28', ...(options.headers || {}) }
  });
  if (!res.ok) throw new Error(`GitHub API ${res.status}: ${(await res.text()).slice(0, 300)}`);
  return res.status === 204 ? null : res.json();
}

async function putFile(path, contentB64, message) {
  return github(`contents/${encodeURI(path)}`, { method: 'PUT', body: JSON.stringify({ message, content: contentB64, branch: $('branch').value.trim() }) });
}

form.addEventListener('submit', async (e) => {
  e.preventDefault(); submitBtn.disabled = true;
  try {
    const config = collectConfig(); validateConfig(config);
    const id = requestId(); const base = `requests/${id}`;
    const icon = $('icon').files[0], splash = $('splash').files[0], zip = $('siteZip').files[0];
    if ([icon, splash, zip].filter(Boolean).some(f => f.size > 20 * 1024 * 1024)) throw new Error('單一檔案不可超過 20 MB。');

    setStatus('1/5 上傳設定…');
    await putFile(`${base}/config.json`, btoa(unescape(encodeURIComponent(JSON.stringify(config, null, 2)))), `Add Web2IPA request ${id}`);
    setStatus('2/5 上傳 App 圖示…');
    await putFile(`${base}/icon${icon.name.substring(icon.name.lastIndexOf('.')) || '.png'}`, await fileToBase64(icon), `Add icon for ${id}`);
    if (splash) { setStatus('3/5 上傳啟動畫面…'); await putFile(`${base}/splash${splash.name.substring(splash.name.lastIndexOf('.')) || '.png'}`, await fileToBase64(splash), `Add splash for ${id}`); }
    if (zip && config.sourceMode === 'offline') { setStatus('4/5 上傳網站 ZIP…'); await putFile(`${base}/site.zip`, await fileToBase64(zip), `Add offline site for ${id}`); }

    setStatus('5/5 觸發 GitHub Actions…');
    await github('dispatches', { method: 'POST', body: JSON.stringify({ event_type: 'build-web2ipa', client_payload: { request_id: id } }) });
    const actionsUrl = `https://github.com/${$('owner').value.trim()}/${$('repo').value.trim()}/actions`;
    setStatus(`已送出！請到 Actions 查看，完成後在該次執行的 Artifacts 下載 IPA：${actionsUrl}`);
  } catch (err) { setStatus(`失敗：${err.message}`); }
  finally { submitBtn.disabled = false; }
});

$('saveBtn').addEventListener('click', () => {
  const data = { github: { owner: $('owner').value, repo: $('repo').value, branch: $('branch').value }, config: collectConfig() };
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type:'application/json'})); a.download = 'web2ipa-settings.json'; a.click(); URL.revokeObjectURL(a.href);
});
$('loadBtn').addEventListener('click', () => $('loadFile').click());
$('loadFile').addEventListener('change', async () => {
  try {
    const data = JSON.parse(await $('loadFile').files[0].text());
    if (data.github) ['owner','repo','branch'].forEach(k => { if (data.github[k] != null) $(k).value = data.github[k]; });
    const c = data.config || data;
    Object.entries(c).forEach(([k,v]) => {
      const el = $(k); if (!el) return;
      if (el.type === 'checkbox') el.checked = !!v; else el.value = v;
    });
    const radio = document.querySelector(`input[name="sourceMode"][value="${c.sourceMode || 'url'}"]`); if (radio) { radio.checked = true; radio.dispatchEvent(new Event('change')); }
    setStatus('設定已載入；圖片與網站 ZIP 需重新選擇。');
  } catch (e) { setStatus(`載入失敗：${e.message}`); }
});

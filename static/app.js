const filesInput = document.getElementById('files');
const uploadBtn = document.getElementById('uploadBtn');
const uploadResult = document.getElementById('uploadResult');
const refreshBtn = document.getElementById('refreshBtn');
const tbody = document.getElementById('tbody');
const counts = document.getElementById('counts');

function setStatus(message, isError = false) {
  uploadResult.textContent = message || '';
  uploadResult.classList.toggle('status-error', Boolean(isError));
}

function formatErrorMessage(payload) {
  if (!payload || typeof payload !== 'object') {
    return '';
  }

  const parts = [];
  if (typeof payload.error === 'string' && payload.error.trim()) {
    parts.push(payload.error.trim());
  }
  if (typeof payload.code === 'string' && payload.code.trim()) {
    parts.push(`[${payload.code.trim()}]`);
  }
  if (typeof payload.detail === 'string' && payload.detail.trim()) {
    parts.push(payload.detail.trim());
  }

  return parts.join(' ').trim();
}

uploadBtn.addEventListener('click', async () => {
  const files = filesInput.files;
  if (!files || !files.length) {
    alert('Select one or more .log files');
    return;
  }
  const fd = new FormData();
  for (const f of files) fd.append('files', f);

  uploadBtn.disabled = true;
  setStatus('Uploading...');

  try {
    const res = await fetch('/api/upload', { method: 'POST', body: fd });
    const isJson = res.headers.get('content-type')?.includes('application/json');
    const payload = isJson ? await res.json() : await res.text();

    if (!res.ok) {
      let message = res.statusText || 'Upload failed';
      if (isJson) {
        const formatted = formatErrorMessage(payload);
        if (formatted) {
          message = formatted;
        }
      }
      throw new Error(message);
    }

    if (isJson && payload && typeof payload === 'object') {
      setStatus(formatUploadResult(payload));
    } else {
      setStatus(String(payload));
    }
    await refresh();
  } catch (e) {
    setStatus('Error: ' + (e && e.message ? e.message : 'Unknown error occurred'), true);
  } finally {
    uploadBtn.disabled = false;
  }
});

refreshBtn.addEventListener('click', refresh);

async function refresh() {
  try {
    const [countsRes, recRes] = await Promise.all([
      fetch('/api/counts'),
      fetch('/api/records?limit=1000&offset=0')
    ]);

    if (!countsRes.ok) {
      const msg = await safeReadText(countsRes);
      throw new Error(msg || `Counts request failed (${countsRes.status})`);
    }
    if (!recRes.ok) {
      const msg = await safeReadText(recRes);
      throw new Error(msg || `Records request failed (${recRes.status})`);
    }

    const c = await countsRes.json();
    counts.textContent = `Antenna hits: ${c.antenna_hits}\nUnique fish: ${c.unique_fish}`;

    const rows = await recRes.json();
    rows.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
    tbody.innerHTML = '';
    const frag = document.createDocumentFragment();
    for (const r of rows) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${r.gate}</td><td>${r.timestamp}</td><td>${r.fishid}</td><td>${r.logfile}</td>`;
      frag.appendChild(tr);
    }
    tbody.appendChild(frag);
  } catch (e) {
    setStatus('Error refreshing data: ' + (e && e.message ? e.message : 'Unknown error'), true);
  }
}

// initial load
refresh();

function formatUploadResult(data) {
  if (!data || typeof data !== 'object') {
    return '';
  }

  const lines = [];

  if (Array.isArray(data.details) && data.details.length) {
    lines.push('Details:');
    for (const detail of data.details) {
      const parts = [];
      if (detail.file) parts.push(`File: ${detail.file}`);
      if (typeof detail.added === 'number') parts.push(`Added: ${detail.added}`);
      if (typeof detail.dummy_removed === 'number') {
        parts.push(`Dummy removed: ${detail.dummy_removed}`);
      }
      lines.push(`  - ${parts.join(', ')}`);
    }
  }

  if (data.summary && typeof data.summary === 'object') {
    lines.push('Summary:');
    if (typeof data.summary.total_added === 'number') {
      lines.push(`  Total added: ${data.summary.total_added}`);
    }
    if (typeof data.summary.total_dummy_removed === 'number') {
      lines.push(`  Total dummy removed: ${data.summary.total_dummy_removed}`);
    }
  }

  return lines.join('\n');
}

async function safeReadText(res) {
  try {
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const body = await res.json();
      if (body && typeof body === 'object') {
        const formatted = formatErrorMessage(body);
        if (formatted) {
          return formatted;
        }
        if (typeof body.message === 'string' && body.message.trim()) {
          return body.message.trim();
        }
        return JSON.stringify(body);
      }
    }
    return await res.text();
  } catch (err) {
    return '';
  }
}

const filesInput = document.getElementById('files');
const uploadBtn = document.getElementById('uploadBtn');
const uploadResult = document.getElementById('uploadResult');
const refreshBtn = document.getElementById('refreshBtn');
const tbody = document.getElementById('tbody');
const counts = document.getElementById('counts');

uploadBtn.addEventListener('click', async () => {
  const files = filesInput.files;
  if (!files || !files.length) {
    alert('Select one or more .log files');
    return;
  }
  const fd = new FormData();
  for (const f of files) fd.append('files', f);

  uploadBtn.disabled = true;
  uploadResult.textContent = 'Uploading...';

  try {
    const res = await fetch('/api/upload', { method: 'POST', body: fd });
    const isJson = res.headers.get('content-type')?.includes('application/json');
    const payload = isJson ? await res.json() : await res.text();

    if (!res.ok) {
      const message = isJson && payload && payload.error ? payload.error : res.statusText;
      throw new Error(message || 'Upload failed');
    }

    if (isJson && payload && typeof payload === 'object') {
      uploadResult.textContent = formatUploadResult(payload);
    } else {
      uploadResult.textContent = String(payload);
    }
    await refresh();
  } catch (e) {
    uploadResult.textContent = 'Error: ' + e.message;
  } finally {
    uploadBtn.disabled = false;
  }
});

refreshBtn.addEventListener('click', refresh);

async function refresh() {
  const [countsRes, recRes] = await Promise.all([
    fetch('/api/counts'),
    fetch('/api/records?limit=1000&offset=0')
  ]);
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

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
    const data = await res.json();
    uploadResult.textContent = JSON.stringify(data, null, 2);
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

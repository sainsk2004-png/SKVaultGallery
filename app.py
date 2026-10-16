
import os
import sqlite3
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from telethon import TelegramClient
from telethon.tl.types import PeerChannel

load_dotenv()

_api_id = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

if not _api_id or not API_HASH:
    raise RuntimeError(
        "Missing TELEGRAM_API_ID or TELEGRAM_API_HASH in .env"
    )

API_ID = int(_api_id)
CHANNEL_ID = 3860912482
DB = Path(__file__).with_name("skvault.db")
CACHE = Path(__file__).with_name("preview_cache")
CACHE.mkdir(exist_ok=True)
MAX_CACHE_BYTES = 500 * 1024 * 1024

client = TelegramClient("skvault_session", API_ID, API_HASH)


@asynccontextmanager
async def lifespan(app):
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Telegram session expired. Run check_channel.py.")
    yield
    await client.disconnect()


app = FastAPI(title="SK Vault Gallery", lifespan=lifespan)


def query_db(sql, args=()):
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(sql, args).fetchall()]


def category(ext, mime):
    ext = (ext or "").lower()
    mime = (mime or "").lower()

    if mime.startswith("image/") or ext in (
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"
    ):
        return "Images"
    if mime.startswith("video/") or ext in (
        ".mp4", ".mkv", ".mov", ".avi", ".webm"
    ):
        return "Videos"
    if mime.startswith("audio/") or ext in (
        ".mp3", ".wav", ".ogg", ".m4a", ".flac"
    ):
        return "Audio"
    if ext == ".pdf" or mime == "application/pdf":
        return "PDFs"
    if ext in (".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"):
        return "Archives"
    if ext in (".doc", ".docx", ".odt", ".rtf"):
        return "Documents"
    if ext in (".xls", ".xlsx", ".csv", ".ods"):
        return "Spreadsheets"
    if ext in (".ppt", ".pptx", ".odp"):
        return "Presentations"
    if ext in (".exe", ".msi", ".apk"):
        return "Applications"
    return "Other"


@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(PAGE)


@app.get("/api/files")
async def files(
    q: str = Query("", max_length=200),
    kind: str = "All",
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    rows = query_db("""
        SELECT message_id, filename, file_type, mime_type,
               size_bytes, message_date, caption
        FROM files
        WHERE filename LIKE ? OR caption LIKE ?
        ORDER BY message_id DESC
    """, (f"%{q}%", f"%{q}%"))

    if kind != "All":
        rows = [
            r for r in rows
            if category(r["file_type"], r["mime_type"]) == kind
        ]

    total = len(rows)

    for row in rows:
        row["category"] = category(row["file_type"], row["mime_type"])
        size = row["size_bytes"] or 0
        if size >= 1024 * 1024:
            row["size_label"] = f"{size / (1024 * 1024):.2f} MB"
        elif size:
            row["size_label"] = f"{size / 1024:.1f} KB"
        else:
            row["size_label"] = "Unknown size"

    return {"total": total, "files": rows[offset:offset + limit]}


def trim_cache():
    entries = sorted(
        (p for p in CACHE.iterdir() if p.is_file()),
        key=lambda p: p.stat().st_atime,
    )
    total = sum(p.stat().st_size for p in entries)

    for path in entries:
        if total <= MAX_CACHE_BYTES:
            break
        size = path.stat().st_size
        try:
            path.unlink()
            total -= size
        except OSError:
            pass


async def get_cached_media(message_id):
    existing = list(CACHE.glob(f"{message_id}.*"))
    if existing:
        existing[0].touch()
        return existing[0]

    channel = await client.get_entity(PeerChannel(CHANNEL_ID))
    message = await client.get_messages(channel, ids=message_id)

    if not message or not message.media:
        raise HTTPException(404, "Telegram media not found")

    filename = message.file.name if message.file else None
    suffix = Path(filename).suffix if filename else ""
    target = CACHE / f"{message_id}{suffix}"

    downloaded = await client.download_media(message, file=str(target))
    if not downloaded:
        raise HTTPException(404, "Unable to retrieve this media")

    trim_cache()
    return Path(downloaded)


@app.get("/preview/{message_id}")
async def preview(message_id: int):
    path = await get_cached_media(message_id)
    return FileResponse(
        path, filename=path.name, content_disposition_type="inline"
    )


@app.get("/download/{message_id}")
async def download(message_id: int):
    path = await get_cached_media(message_id)
    return FileResponse(
        path, filename=path.name, content_disposition_type="attachment"
    )


PAGE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SK Vault Gallery</title>
<style>
:root {
  color-scheme: dark;
  --bg:#0b1120; --panel:#172235; --border:#334155;
  --text:#f1f5f9; --muted:#a9b8cc; --accent:#93c5fd;
}
* {box-sizing:border-box}
body {margin:0;background:var(--bg);color:var(--text);
      font:15px/1.45 system-ui,sans-serif}
header {padding:22px;background:var(--panel);
        border-bottom:1px solid var(--border);
        position:sticky;top:0;z-index:5}
h1 {margin:0 0 4px;font-size:25px}
.subtitle,.meta {color:var(--muted);font-size:12px}
.controls {display:flex;gap:9px;margin-top:17px;flex-wrap:wrap}
input,select,button {color:var(--text);background:#0b1120;
  border:1px solid var(--border);border-radius:9px;padding:11px 13px;
  font:inherit}
input {flex:1;min-width:180px}
button {cursor:pointer}
button:hover {border-color:var(--accent)}
button:disabled {opacity:.65;cursor:wait}
main {padding:18px}
.toolbar {display:flex;justify-content:space-between;gap:12px;
          flex-wrap:wrap;align-items:center;margin:2px 0 16px}
#status {color:var(--muted)}
.grid {display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:15px}
.card {min-width:0;overflow:hidden;border:1px solid var(--border);
  border-radius:13px;background:var(--panel);display:flex;flex-direction:column}
.thumb {height:190px;background:#080e1b;display:flex;align-items:center;
  justify-content:center;overflow:hidden;position:relative}
.thumb img,.thumb video {width:100%;height:100%;object-fit:contain}
.thumb img {cursor:zoom-in}
.file-icon {color:var(--muted);font-size:38px;font-weight:700}
.info {padding:13px;display:flex;flex-direction:column;gap:8px;flex:1}
.name {font-weight:650;overflow-wrap:anywhere;line-height:1.35}
.meta {line-height:1.5}
.actions {display:flex;gap:8px;flex-wrap:wrap;margin-top:auto;padding-top:3px}
.actions a {text-decoration:none;color:var(--accent);border:1px solid var(--border);
  border-radius:7px;padding:7px 10px;font-size:13px}
.actions a:hover {background:#24334a}
#more {margin:20px 0}
dialog {width:min(94vw,1200px);max-width:1200px;max-height:92vh;
  padding:12px;background:#101827;color:var(--text);
  border:1px solid var(--border);border-radius:12px}
dialog::backdrop {background:rgba(0,0,0,.85)}
#viewerImage {display:block;max-width:100%;max-height:78vh;margin:auto;object-fit:contain}
.viewerBar {display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:10px}
@media(max-width:600px) {
  header {padding:15px;position:static}
  main {padding:12px}
  .grid {grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
  .thumb {height:140px}
  .info {padding:10px}
}
</style>
</head>
<body>
<header>
  <h1>SK Vault Gallery</h1>
  <div class="subtitle">Telegram cloud gallery · Images load as you scroll</div>
  <div class="controls">
    <input id="q" type="search" placeholder="Search filenames or captions…">
    <select id="kind" aria-label="Filter by file type">
      <option>All</option><option>Images</option><option>Videos</option>
      <option>Audio</option><option>PDFs</option><option>Documents</option>
      <option>Spreadsheets</option><option>Presentations</option>
      <option>Archives</option><option>Applications</option><option>Other</option>
    </select>
    <button id="search">Search</button>
  </div>
</header>
<main>
  <div class="toolbar">
    <div id="status">Loading index…</div>
    <div class="subtitle">Preview cache target: 500 MB</div>
  </div>
  <div id="grid" class="grid"></div>
  <button id="more" hidden>Load more</button>
</main>

<dialog id="viewer">
  <div class="viewerBar">
    <span id="viewerTitle"></span>
    <button id="closeViewer">Close</button>
  </div>
  <img id="viewerImage" alt="">
</dialog>

<script>
const q=document.getElementById('q');
const kind=document.getElementById('kind');
const grid=document.getElementById('grid');
const status=document.getElementById('status');
const more=document.getElementById('more');
const viewer=document.getElementById('viewer');
const viewerImage=document.getElementById('viewerImage');
const viewerTitle=document.getElementById('viewerTitle');

let offset=0,busy=false,timer=null;
let observer=null;
const objectUrls=new Set();

function esc(s) {
  return String(s??'').replace(/[&<>"']/g,c=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}
function prettyDate(s) {
  if(!s)return 'Date unknown';
  const d=new Date(s);
  return Number.isNaN(d.getTime())?'Date unknown':d.toLocaleDateString();
}
function imageType(f) {
  return f.category==='Images';
}
function makeCard(f) {
  const card=document.createElement('article');
  card.className='card';

  const thumb=document.createElement('div');
  thumb.className='thumb';

  if(imageType(f)) {
    const img=document.createElement('img');
    img.alt=f.filename;
    img.loading='lazy';
    img.decoding='async';
    img.dataset.preview=`/preview/${f.message_id}`;
    img.dataset.loaded='false';
    img.title='Click to enlarge';
    img.addEventListener('click',()=>openViewer(f,img.src));
    thumb.appendChild(img);
    observer.observe(img);
  } else if(f.category==='Videos') {
    const btn=document.createElement('button');
    btn.textContent='Load video preview';
    btn.addEventListener('click',()=>loadVideo(f,thumb,btn));
    thumb.appendChild(btn);
  } else {
    const icon=document.createElement('div');
    icon.className='file-icon';
    icon.textContent=f.category==='PDFs'?'PDF':
      f.category==='Archives'?'ZIP':f.category==='Audio'?'♪':'FILE';
    thumb.appendChild(icon);
  }

  const info=document.createElement('div');
  info.className='info';

  const name=document.createElement('div');
  name.className='name';
  name.textContent=f.filename;

  const meta=document.createElement('div');
  meta.className='meta';
  meta.textContent=`${f.category} · ${f.size_label} · ${prettyDate(f.message_date)}`;

  const actions=document.createElement('div');
  actions.className='actions';
  const link=document.createElement('a');
  link.href=`/download/${f.message_id}`;
  link.textContent='Download file';
  actions.appendChild(link);

  info.append(name,meta,actions);
  card.append(thumb,info);
  return card;
}

async function fetchPreview(url) {
  const response=await fetch(url);
  if(!response.ok)throw new Error(`Preview failed (${response.status})`);
  const blob=await response.blob();
  const objectUrl=URL.createObjectURL(blob);
  objectUrls.add(objectUrl);
  return objectUrl;
}

async function loadImage(img) {
  if(img.dataset.loaded==='true'||img.dataset.loading==='true')return;
  img.dataset.loading='true';
  try {
    const url=await fetchPreview(img.dataset.preview);
    img.onload=()=>{img.dataset.loaded='true';img.dataset.loading='false';};
    img.onerror=()=>{
      img.dataset.loading='false';
      img.alt='Preview unavailable';
      img.style.cursor='default';
    };
    img.src=url;
  } catch(e) {
    img.dataset.loading='false';
    img.alt='Preview unavailable — retry by refreshing';
  }
}

async function loadVideo(f,thumb,btn) {
  btn.disabled = true;
  btn.textContent = 'Loading video…';

  const video = document.createElement('video');
  video.controls = true;
  video.preload = 'metadata';
  video.playsInline = true;
  video.src = `/preview/${f.message_id}`;

  video.addEventListener('loadedmetadata', () => {
    btn.remove();
    status.textContent = 'Video preview ready.';
  }, { once: true });

  video.addEventListener('error', () => {
    btn.disabled = false;
    btn.textContent = 'Retry preview';
    status.textContent = 'Video preview failed. The file may use an unsupported format or the server may not be serving it correctly.';
  });

  thumb.replaceChildren(video);
  video.load();
}

function openViewer(f,url) {
  viewerTitle.textContent=f.filename;
  viewerImage.src=url;
  viewerImage.alt=f.filename;
  viewer.showModal();
}
document.getElementById('closeViewer').addEventListener('click',()=>viewer.close());
viewer.addEventListener('click',e=>{if(e.target===viewer)viewer.close();});

async function loadFiles(reset=false) {
  if(busy)return;
  busy=true;
  if(reset) {
    if(observer)observer.disconnect();
    offset=0;
    grid.replaceChildren();
    observer=new IntersectionObserver(entries=>{
      for(const entry of entries) {
        if(entry.isIntersecting) {
          observer.unobserve(entry.target);
          loadImage(entry.target);
        }
      }
    },{rootMargin:'300px 0px',threshold:0.01});
  }
  status.textContent='Searching index…';
  try {
    const params=new URLSearchParams({
      q:q.value,kind:kind.value,limit:'100',offset:String(offset)
    });
    const response=await fetch(`/api/files?${params}`);
    if(!response.ok)throw new Error(`Request failed (${response.status})`);
    const data=await response.json();
    for(const file of data.files)grid.appendChild(makeCard(file));
    offset+=data.files.length;
    status.textContent=`${data.total.toLocaleString()} matching files · ${offset.toLocaleString()} shown`;
    more.hidden=offset>=data.total;
    if(!data.files.length&&offset===0)status.textContent='No matching files found.';
  } catch(e) {
    status.textContent=`Could not load index: ${e.message}`;
  } finally {
    busy=false;
  }
}

document.getElementById('search').addEventListener('click',()=>loadFiles(true));
q.addEventListener('input',()=>{
  clearTimeout(timer);
  timer=setTimeout(()=>loadFiles(true),300);
});
kind.addEventListener('change',()=>loadFiles(true));
more.addEventListener('click',()=>loadFiles(false));

window.addEventListener('beforeunload',()=>{
  for(const url of objectUrls)URL.revokeObjectURL(url);
});

loadFiles(true);
</script>
</body>
</html>
"""

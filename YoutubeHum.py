import os
import asyncio
import threading
import queue
import sqlite3
import time
import certifi
import yt_dlp
import shutil
import pandas as pd
import streamlit as st
from datetime import datetime
from pathlib import Path
import random

# =========================================================
# CORE CONFIGURATION & CONSTANTS
# =========================================================
os.environ['SSL_CERT_FILE'] = certifi.where()

class Config:
    VERSION = "7.0-TITAN"
    DB_NAME = "yt_hum_pro.db"
    CHUNK_SIZE = 1024 * 1024 * 10  # 10MB
    MAX_PLAYLIST_SIZE = 200
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/13.1.3"
    ]

# =========================================================
# DATABASE SERVICE (PERSISTENCE & STATS)
# =========================================================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_NAME, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        with self.conn:
            self.conn.execute('''CREATE TABLE IF NOT EXISTS downloads 
                (id INTEGER PRIMARY KEY, url TEXT UNIQUE, title TEXT, 
                status TEXT, path TEXT, size REAL, date TEXT)''')
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_url ON downloads(url)")

    def save_download(self, url, title, status, path, size):
        with self.conn:
            self.conn.execute("""INSERT OR REPLACE INTO downloads (url, title, status, path, size, date) 
                                 VALUES (?, ?, ?, ?, ?, ?)""", 
                              (url, title, status, path, size, datetime.now().isoformat()))

    def get_history(self, limit=50, offset=0):
        return pd.read_sql_query(f"SELECT * FROM downloads ORDER BY id DESC LIMIT {limit} OFFSET {offset}", self.conn)

    def clear_history(self):
        with self.conn: self.conn.execute("DELETE FROM downloads")

# =========================================================
# ASYNC ENGINE (PARALLELISM & LOGIC)
# =========================================================
class TitanEngine:
    def __init__(self, db):
        self.db = db
        self.queue = asyncio.Queue()
        self.out_queue = queue.Queue()
        self.semaphore = None # Sera initialisé dans l'event loop
        self.stop_event = asyncio.Event()
        self.is_paused = False
        self.active_tasks = {}

    async def start_workers(self, worker_count):
        self.semaphore = asyncio.Semaphore(worker_count)
        while not self.stop_event.is_set():
            url, opts = await self.queue.get()
            asyncio.create_task(self._worker_wrapper(url, opts))
            self.queue.task_done()

    async def _worker_wrapper(self, url, opts):
        async with self.semaphore:
            if self.is_paused:
                while self.is_paused: await asyncio.sleep(1)
            await self._execute_download(url, opts)

    async def _execute_download(self, url, opts):
        # Vérification espace disque
        total, used, free = shutil.disk_usage(os.path.dirname(opts['outtmpl']))
        if free < 500 * 1024 * 1024: # < 500MB
            self.out_queue.put({'type': 'error', 'url': url, 'msg': 'Espace disque insuffisant'})
            return

        def hook(d):
            if d['status'] == 'downloading':
                self.out_queue.put({
                    'type': 'progress', 'url': url, 
                    'p': d.get('downloaded_bytes', 0) / d.get('total_bytes', 1),
                    'speed': d.get('_speed_str', 'N/A'), 'eta': d.get('_eta_str', 'N/A')
                })

        opts.update({
            'progress_hooks': [hook],
            'user_agent': random.choice(Config.USER_AGENTS),
            'noprogress': True,
        })

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=True)
                size = (info.get('filesize') or 0) / 1048576
                self.out_queue.put({'type': 'success', 'url': url, 'title': info['title'], 'size': size, 'path': opts['outtmpl']})
                self.db.save_download(url, info['title'], "SUCCESS", opts['outtmpl'], size)
        except Exception as e:
            self.out_queue.put({'type': 'error', 'url': url, 'msg': f"{type(e).__name__}"})
            self.db.save_download(url, "Error", "FAILED", "", 0)

# =========================================================
# STREAMLIT UI (CONTROL TOWER)
# =========================================================
st.set_page_config(page_title="YoutubeHum Titan", layout="wide")

if 'titan' not in st.session_state:
    st.session_state.db = Database()
    st.session_state.titan = TitanEngine(st.session_state.db)
    st.session_state.monit = {}
    
    # Threading de l'event loop asyncio
    def run_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(st.session_state.titan.start_workers(2))
    threading.Thread(target=run_async, daemon=True).start()

# Communication Engine -> UI
while not st.session_state.titan.out_queue.empty():
    msg = st.session_state.titan.out_queue.get()
    if msg['type'] == 'progress': st.session_state.monit[msg['url']] = msg
    elif msg['type'] in ['success', 'error']: 
        if msg['url'] in st.session_state.monit: del st.session_state.monit[msg['url']]

# --- UI LAYOUT ---
st.title(f"🚀 {Config.VERSION}")

with st.sidebar:
    st.header("🎮 Dashboard")
    st.session_state.titan.is_paused = st.toggle("⏸️ Pause Engine")
    worker_limit = st.slider("Workers Simultanés", 1, 8, 2)
    if st.button("🗑️ Vider Historique"): st.session_state.db.clear_history()
    
    st.divider()
    st.write(f"💾 RAM: {st.session_state.get('ram', 'N/A')}") # Placeholder stats
    
# --- AJOUT TACHES ---
with st.expander("➕ Ajouter des téléchargements", expanded=True):
    u_col, p_col = st.columns([3, 1])
    urls = u_col.text_area("URLs (une par ligne)")
    folder = p_col.text_input("Dossier", value=str(Path.home() / "Downloads"))
    mode = st.selectbox("Format", ["MP4 (Vidéo)", "MP3 (Audio)"])
    
    if st.button("Lancer la Queue", use_container_width=True):
        for u in urls.split('\n'):
            if u.strip():
                opts = {
                    'outtmpl': os.path.join(folder, '%(title).80s.%(ext)s'),
                    'format': 'bestaudio/best' if mode == "MP3" else 'bestvideo+bestaudio/best',
                }
                if mode == "MP3": opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]
                st.session_state.titan.queue.put_nowait((u.strip(), opts))
        st.toast("Tâches injectées !")

# --- MONITORING ---
st.subheader("🛰️ Monitoring en temps réel")
if not st.session_state.monit:
    st.info("Aucun téléchargement actif.")
else:
    for url, data in list(st.session_state.monit.items()):
        col1, col2, col3 = st.columns([1, 4, 1])
        col1.caption(data['speed'])
        col2.progress(data['p'], text=f"{url[:50]}...")
        col3.caption(f"ETA: {data['eta']}")

# --- HISTORIQUE ---
st.subheader("📜 Historique")
df = st.session_state.db.get_history()
st.dataframe(df, use_container_width=True)

# Boucle de rafraîchissement
time.sleep(1)
st.rerun()
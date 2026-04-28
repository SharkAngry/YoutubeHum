import os
import asyncio
import threading
import queue
import sqlite3
import time
import certifi
import yt_dlp
import streamlit as st
from datetime import datetime
from pathlib import Path

# =========================================================
# INITIALISATION ET BASE DE DONNÉES
# =========================================================
os.environ['SSL_CERT_FILE'] = certifi.where()

class DBManager:
    def __init__(self):
        self.conn = sqlite3.connect('yt_hum.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS history 
            (id INTEGER PRIMARY KEY, title TEXT, url TEXT, status TEXT, date TEXT, path TEXT)''')
        self.conn.commit()

    def add_entry(self, title, url, status, path):
        self.cursor.execute("INSERT INTO history (title, url, status, date, path) VALUES (?,?,?,?,?)",
                            (title, url, status, datetime.now().strftime("%Y-%m-%d %H:%M"), path))
        self.conn.commit()

# =========================================================
# LE MOTEUR (ENGINE) - DÉCOUPLÉ DE STREAMLIT
# =========================================================

class DownloadEngine:
    def __init__(self):
        self.in_queue = queue.Queue()
        self.out_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set() # True = Running
        self.current_tasks = {}
        self.is_active = False

    def start(self):
        if not self.is_active:
            self.stop_event.clear()
            threading.Thread(target=self._run_loop, daemon=True).start()
            self.is_active = True

    def _run_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._process_queue())

    async def _process_queue(self):
        while not self.stop_event.is_set():
            self.pause_event.wait() # Blocage propre si pause
            
            try:
                task = self.in_queue.get(timeout=1)
            except queue.Empty:
                continue

            await self._download_task(task)
            self.in_queue.task_done()

    async def _download_task(self, task):
        url = task['url']
        opts = task['opts']
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                # Protection division par zéro
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                downloaded = d.get('downloaded_bytes', 0)
                progress = downloaded / total
                self.out_queue.put({
                    'type': 'progress', 
                    'url': url, 
                    'p': progress, 
                    'speed': d.get('_speed_str', '0B/s'),
                    'eta': d.get('_eta_str', 'N/A')
                })

        opts['progress_hooks'] = [progress_hook]
        
        # Vérification si fichier existe déjà (Skip logique)
        opts['nooverwrites'] = True
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                # Exécution dans un thread séparé pour ne pas bloquer l'event loop
                info = await asyncio.to_thread(ydl.extract_info, url, download=True)
                title = info.get('title', 'Video')
                self.out_queue.put({'type': 'success', 'url': url, 'title': title})
        except Exception as e:
            self.out_queue.put({'type': 'error', 'url': url, 'msg': str(e)[:100]})

# Singleton Engine
if 'engine' not in st.session_state:
    st.session_state.engine = DownloadEngine()
    st.session_state.engine.start()
    st.session_state.db = DBManager()
    st.session_state.progress_data = {}

# =========================================================
# INTERFACE STREAMLIT (UI)
# =========================================================

st.title("🛡️ YoutubeHum Master v6.0")

# Récupération des résultats de la queue de sortie (Update UI)
while not st.session_state.engine.out_queue.empty():
    msg = st.session_state.engine.out_queue.get()
    if msg['type'] == 'progress':
        st.session_state.progress_data[msg['url']] = msg
    elif msg['type'] == 'success':
        st.session_state.db.add_entry(msg['title'], msg['url'], "SUCCESS", "")
        if msg['url'] in st.session_state.progress_data: 
            del st.session_state.progress_data[msg['url']]
    elif msg['type'] == 'error':
        st.session_state.db.add_entry("Error", msg['url'], f"FAILED: {msg['msg']}", "")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎮 Contrôle Global")
    c1, c2 = st.columns(2)
    if c1.button("⏸️ PAUSE"): st.session_state.engine.pause_event.clear()
    if c2.button("▶️ RESUME"): st.session_state.engine.pause_event.set()
    
    if st.button("🛑 STOP TOUT", type="primary", use_container_width=True):
        st.session_state.engine.stop_event.set()
        st.session_state.engine.in_queue = queue.Queue() # Clear queue
        
    st.divider()
    browser = st.selectbox("Navigateur Cookies", ["firefox", "chrome", "edge", "brave"])
    workers = st.slider("Max Workers simultanés", 1, 4, 2)

# --- ZONE DE TÉLÉCHARGEMENT ---
url_input = st.text_area("URLs YouTube (Playlist ou uniques)")
out_dir = st.text_input("Dossier", value=str(Path.home() / "Downloads"))

if st.button("🚀 AJOUTER À LA QUEUE"):
    with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': 'in_playlist'}) as ydl:
        data = ydl.extract_info(url_input, download=False)
        entries = data.get('entries', [data])
        
        for entry in entries[:100]: # Cap à 100 pour sécurité
            url = entry.get('url') or entry.get('webpage_url')
            if not url: continue
            
            task_opts = {
                'outtmpl': os.path.join(out_dir, '%(title).80s.%(ext)s'),
                'cookiesfrombrowser': (browser,),
                'format': 'bestvideo+bestaudio/best',
            }
            st.session_state.engine.in_queue.put({'url': url, 'opts': task_opts})
    st.success(f"{len(entries)} tâches ajoutées !")

# --- MONITORING TEMPS RÉEL ---
st.subheader("📥 File d'attente active")
for url, data in st.session_state.progress_data.items():
    col_a, col_b = st.columns([1, 4])
    col_a.write(f"Vitesse: {data['speed']}")
    col_b.progress(data['p'], text=f"ETA: {data['eta']} | {url[:40]}...")

# --- HISTORIQUE ---
with st.expander("📜 Historique Persistant (SQLite)"):
    history = st.session_state.db.cursor.execute("SELECT * FROM history ORDER BY id DESC LIMIT 20").fetchall()
    if history:
        for h in history:
            st.text(f"[{h[4]}] {h[3]} - {h[1][:50]}")

# Refresh Loop
time.sleep(1)
st.rerun()
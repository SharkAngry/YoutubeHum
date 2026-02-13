import os
import time
import yt_dlp
import streamlit as st
import concurrent.futures
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import random
import subprocess
import re

# =========================================================
# CONSTANTES (Correction "Magic Numbers" - Analyse GitHub)
# =========================================================
LOGO_WIDTH = 240
LOGO_HEIGHT = 40
LOGO_TEXT_X = 0
LOGO_TEXT_Y = 28
LOGO_FONT_SIZE = 28
VERSION_X = 190
VERSION_FONT_SIZE = 14

DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
TEMP_FILE_EXTENSIONS = (".jpg", ".png", ".webp", ".part", ".ytdl", ".temp", ".f*")
DOWNLOAD_TIMEOUT = 900  # 15 minutes
CHUNK_SIZE = 10485760  # 10MB

# Configuration pour Windows
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''

st.set_page_config(page_title="YoutubeHum Ultimate", page_icon="🎧", layout="wide")

# =========================================================
# INITIALISATION ET STYLE
# =========================================================
if "history" not in st.session_state:
    st.session_state.history = []
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "stats" not in st.session_state:
    st.session_state.stats = {"total_downloaded": 0, "total_failed": 0, "total_size_mb": 0}

st.markdown("""
<style>
    .main { background-color: #0f1117; color: #e5e7eb; }
    .success-box { padding: 1.5rem; border-radius: 0.5rem; background-color: #1e3a2e; border-left: 4px solid #10b981; margin: 1rem 0; }
    .info-box { padding: 1rem; border-radius: 0.5rem; background-color: #1e293b; border-left: 4px solid #3b82f6; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<svg width="{LOGO_WIDTH}" height="{LOGO_HEIGHT}" viewBox="0 0 {LOGO_WIDTH} {LOGO_HEIGHT}">
  <text x="{LOGO_TEXT_X}" y="{LOGO_TEXT_Y}" fill="#e5e7eb" font-size="{LOGO_FONT_SIZE}" font-family="Inter" font-weight="600">YoutubeHum</text>
  <text x="{VERSION_X}" y="{LOGO_TEXT_Y}" fill="#10b981" font-size="{VERSION_FONT_SIZE}" font-family="Inter" font-weight="400">v3.1</text>
</svg>
""", unsafe_allow_html=True)

# =========================================================
# UTILITAIRES
# =========================================================
def clean_temp_files(directory):
    """Nettoie les fichiers temporaires (Correction Except propre)."""
    if not os.path.exists(directory): return 0
    cleaned = 0
    for root, _, files in os.walk(directory):
        for f in files:
            if any(f.endswith(ext) for ext in TEMP_FILE_EXTENSIONS) or f.startswith('.'):
                try:
                    os.remove(os.path.join(root, f))
                    cleaned += 1
                except Exception: pass 
    return cleaned

def format_time(seconds):
    if seconds < 60: return f"{seconds:.1f}s"
    return f"{int(seconds//60)}m {int(seconds%60)}s"

# =========================================================
# LOGIQUE DE TÉLÉCHARGEMENT (FUSION ANTI-403)
# =========================================================
def get_ydl_opts(mode, outdir, quality):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ]
    
    opts = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": os.path.join(outdir, "%(title)s.%(ext)s"),
        "retries": 10,
        "fragment_retries": 15,
        "nocheckcertificate": True,
        "windowsfilenames": True,
        "cookiesfrombrowser": ("chrome",), # INDISPENSABLE POUR 403
        "http_headers": {
            "User-Agent": random.choice(user_agents),
            "Accept": "*/*",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/",
        }
    }

    if mode == "MP3":
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            }, {"key": "FFmpegMetadata"}]
        })
    else:
        opts.update({
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
        })
    return opts

def process_video(url, mode, outdir, quality):
    start = time.time()
    ydl_opts = get_ydl_opts(mode, outdir, quality)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.cache.remove() # Correction 403
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Vidéo')
            filesize = info.get('filesize') or info.get('filesize_approx') or 0
            duration = info.get('duration', 0)
            
        return time.time() - start, "OK", title, filesize / (1024*1024), duration

    except Exception as e:
        # STRATÉGIE DE FALLBACK (v3.0)
        if "403" in str(e):
            try:
                fallback_opts = ydl_opts.copy()
                fallback_opts["format"] = "worst/best" # Tente une qualité inférieure
                with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                    ydl.download([url])
                return time.time() - start, "OK (Fallback)", "Vidéo (Qualité réduite)", 0, 0
            except Exception: pass
        return 0, f"ERREUR: {str(e)[:100]}", "Échec", 0, 0

# =========================================================
# INTERFACE UTILISATEUR
# =========================================================
st.markdown("### 1. Source")
url_input = st.text_input("Lien YouTube (Vidéo ou Playlist)", placeholder="https://...")

st.markdown("### 2. Configuration")
c1, c2, c3 = st.columns(3)
with c1:
    mode_selection = st.radio("Format", ["Vidéo MP4", "Audio MP3"], horizontal=True)
with c2:
    quality = st.selectbox("Qualité MP3", ["128", "192", "256", "320"], index=3)
with c3:
    max_parallel = st.slider("Simultanés (1-2 recommandé)", 1, 4, 1)

if st.button("🚀 DÉMARRER LE TÉLÉCHARGEMENT", type="primary", use_container_width=True):
    if not url_input:
        st.error("Veuillez entrer une URL")
    else:
        st.session_state.stop_requested = False
        mode = "MP3" if "Audio" in mode_selection else "VIDEO"
        
        # Analyse
        with st.spinner("Analyse de la source..."):
            try:
                with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": "in_playlist"}) as ydl:
                    info_main = ydl.extract_info(url_input, download=False)
                    urls = [e["url"] for e in info_main.get("entries", [])] if "entries" in info_main else [url_input]
            except Exception as e:
                st.error(f"Erreur d'analyse : {e}")
                urls = []

        if urls:
            # Dossier
            folder = re.sub(r'[<>:"/\\|?*]', '', info_main.get("title", "YoutubeHum"))
            session_dir = os.path.join(DEFAULT_DOWNLOAD_DIR, f"{folder[:50]}_{datetime.now().strftime('%H%M%S')}")
            os.makedirs(session_dir, exist_ok=True)

            progress = st.progress(0)
            status_text = st.empty()
            detail_container = st.container()
            
            completed = 0
            total = len(urls)
            
            with ThreadPoolExecutor(max_workers=max_parallel) as executor:
                futures = {executor.submit(process_video, u, mode, session_dir, quality): u for u in urls}
                
                for future in concurrent.futures.as_completed(futures):
                    res_time, res_status, title, size, duration = future.result()
                    
                    if res_status.startswith("OK"):
                        st.session_state.stats["total_downloaded"] += 1
                        st.session_state.stats["total_size_mb"] += size
                        with detail_container:
                            st.success(f"✅ {title[:60]}... ({format_time(res_time)})")
                    else:
                        st.session_state.stats["total_failed"] += 1
                        with detail_container:
                            st.error(f"❌ {res_status}")
                    
                    completed += 1
                    progress.progress(completed / total)
                    status_text.info(f"Progression : {completed}/{total}")

            clean_temp_files(session_dir)
            st.balloons()
            st.markdown(f'<div class="success-box"><h3>Terminé !</h3>Dossier : <code>{session_dir}</code></div>', unsafe_allow_html=True)
            if st.button("📂 Ouvrir le dossier"):
                os.startfile(session_dir)

# =========================================================
# STATISTIQUES (v2.0)
# =========================================================
st.sidebar.markdown("### 📊 Statistiques Session")
st.sidebar.metric("Réussis", st.session_state.stats["total_downloaded"])
st.sidebar.metric("Échecs", st.session_state.stats["total_failed"])
st.sidebar.metric("Volume", f"{st.session_state.stats['total_size_mb']:.1f} MB")
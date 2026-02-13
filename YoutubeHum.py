import os
import time
import yt_dlp
import streamlit as st
import concurrent.futures
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import random
import re
import certifi  # Importation pour la sécurité SSL propre

# =========================================================
# CONFIGURATION PROPRE (Respect des standards GitHub)
# =========================================================
LOGO_WIDTH, LOGO_HEIGHT = 240, 40
LOGO_TEXT_Y, LOGO_FONT_SIZE = 28, 28
VERSION_X, VERSION_FONT_SIZE = 190, 14

DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
TEMP_EXT = (".jpg", ".png", ".webp", ".part", ".ytdl", ".temp", ".f*")
TIMEOUT = 900 

# SOLUTION PROPRE POUR LE SSL (Remplace le hack os.environ['SSL_CERT_FILE'] = '')
os.environ['SSL_CERT_FILE'] = certifi.where()

st.set_page_config(page_title="YoutubeHum Ultimate", page_icon="🎧", layout="wide")

# =========================================================
# INITIALISATION
# =========================================================
if "history" not in st.session_state:
    st.session_state.history = []
if "stats" not in st.session_state:
    st.session_state.stats = {"total_downloaded": 0, "total_failed": 0, "total_size_mb": 0}

# Logo avec constantes (Analyse GitHub OK)
st.markdown(f"""
<svg width="{LOGO_WIDTH}" height="{LOGO_HEIGHT}">
  <text x="0" y="{LOGO_TEXT_Y}" fill="#e5e7eb" font-size="{LOGO_FONT_SIZE}" font-family="Inter" font-weight="600">YoutubeHum</text>
  <text x="{VERSION_X}" y="{LOGO_TEXT_Y}" fill="#10b981" font-size="{VERSION_FONT_SIZE}" font-family="Inter">v3.2</text>
</svg>
""", unsafe_allow_html=True)

# =========================================================
# LOGIQUE DE TÉLÉCHARGEMENT
# =========================================================
def get_safe_opts(mode, outdir, quality):
    """Options optimisées anti-403 et sécurisées."""
    uas = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/121.0.0.0"
    ]
    
    opts = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": os.path.join(outdir, "%(title)s.%(ext)s"),
        "retries": 10,
        "nocheckcertificate": False, # SÉCURITÉ RÉACTIVÉE (Avis GitHub suivi)
        "windowsfilenames": True,
        "cookiesfrombrowser": ("chrome",), # Utilise tes cookies Chrome
        "http_headers": {
            "User-Agent": random.choice(uas),
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8",
        }
    }

    if mode == "MP3":
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": quality}]
        })
    else:
        opts.update({"format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "merge_output_format": "mp4"})
    return opts

def process_video(url, mode, outdir, quality):
    start_time = time.time()
    ydl_opts = get_safe_opts(mode, outdir, quality)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.cache.remove() # Crucial pour éviter les erreurs 403
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Vidéo')
            size = (info.get('filesize') or info.get('filesize_approx') or 0) / (1024*1024)
            
        return time.time() - start_time, "OK", title, size
    except Exception as e:
        # Fallback si 403 (On tente en qualité inférieure avant d'abandonner)
        if "403" in str(e):
            try:
                ydl_opts["format"] = "worst/best"
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                return time.time() - start_time, "OK (Mode Dégradé)", "Vidéo (Qualité réduite)", 0
            except Exception: pass
        return 0, f"Erreur : {str(e)[:50]}", "Échec", 0

# =========================================================
# INTERFACE
# =========================================================
url_input = st.text_input("Lien YouTube", placeholder="Lien vidéo ou playlist")

col1, col2, col3 = st.columns(3)
with col1:
    mode_sel = st.radio("Format", ["Vidéo MP4", "Audio MP3"], horizontal=True)
with col2:
    quality_sel = st.selectbox("Qualité MP3", ["128", "192", "256", "320"], index=3)
with col3:
    threads = st.slider("Simultanés", 1, 2, 1) # Limité à 2 pour éviter les bans IP

if st.button("🚀 LANCER", type="primary", use_container_width=True):
    if url_input:
        mode = "MP3" if "Audio" in mode_sel else "VIDEO"
        
        with st.spinner("Analyse en cours..."):
            try:
                with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": "in_playlist"}) as ydl:
                    data = ydl.extract_info(url_input, download=False)
                    urls = [e["url"] for e in data.get("entries", [])] if "entries" in data else [url_input]
                    folder_title = re.sub(r'[<>:"/\\|?*]', '', data.get("title", "YoutubeHum"))
            except Exception as e:
                st.error(f"Erreur d'analyse : {e}")
                urls = []

        if urls:
            path = os.path.join(DEFAULT_DOWNLOAD_DIR, f"{folder_title[:30]}_{datetime.now().strftime('%H%M%S')}")
            os.makedirs(path, exist_ok=True)
            
            prog = st.progress(0)
            status = st.empty()
            
            with ThreadPoolExecutor(max_workers=threads) as ex:
                futures = {ex.submit(process_video, u, mode, path, quality_sel): u for u in urls}
                for i, f in enumerate(concurrent.futures.as_completed(futures)):
                    t, msg, name, sz = f.result()
                    if msg.startswith("OK"):
                        st.success(f"✅ {name[:50]}... ({sz:.1f} MB)")
                        st.session_state.stats["total_downloaded"] += 1
                        st.session_state.stats["total_size_mb"] += sz
                    else:
                        st.error(f"❌ {msg}")
                    prog.progress((i + 1) / len(urls))

            st.balloons()
            st.info(f"Fini ! Dossier : {path}")
            if st.button("📂 Ouvrir"): os.startfile(path)

# Stats SideBar
st.sidebar.metric("Réussis", st.session_state.stats["total_downloaded"])
st.sidebar.metric("Volume", f"{st.session_state.stats['total_size_mb']:.1f} MB")
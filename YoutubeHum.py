import os
import time
import yt_dlp
import streamlit as st
import concurrent.futures
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import random
import re
import certifi

# =========================================================
# CONSTANTES (Correction Analyse GitHub)
# =========================================================
LOGO_WIDTH = 240
LOGO_HEIGHT = 40
LOGO_TEXT_Y = 28
LOGO_FONT_SIZE = 28
VERSION_X = 190
VERSION_FONT_SIZE = 14

DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
TEMP_EXTENSIONS = (".jpg", ".png", ".webp", ".part", ".ytdl", ".temp", ".f*")
DOWNLOAD_TIMEOUT = 900  # 15 minutes

# SOLUTION SSL PROPRE (Plus de hack os.environ)
os.environ['SSL_CERT_FILE'] = certifi.where()

st.set_page_config(page_title="YoutubeHum Ultimate", page_icon="🎧", layout="wide")

# =========================================================
# STYLE ET INITIALISATION
# =========================================================
if "stats" not in st.session_state:
    st.session_state.stats = {"total_downloaded": 0, "total_failed": 0, "total_size_mb": 0}
if "history" not in st.session_state:
    st.session_state.history = []

st.markdown(f"""
<svg width="{LOGO_WIDTH}" height="{LOGO_HEIGHT}">
  <text x="0" y="{LOGO_TEXT_Y}" fill="#e5e7eb" font-size="{LOGO_FONT_SIZE}" font-family="Inter" font-weight="600">YoutubeHum</text>
  <text x="{VERSION_X}" y="{LOGO_TEXT_Y}" fill="#10b981" font-size="{VERSION_FONT_SIZE}" font-family="Inter">v3.4</text>
</svg>
""", unsafe_allow_html=True)

# =========================================================
# FONCTIONS TECHNIQUES
# =========================================================

def clean_temp_files(directory):
    """Nettoie les fichiers résiduels après téléchargement."""
    if not os.path.exists(directory): return
    for root, _, files in os.walk(directory):
        for f in files:
            if any(f.endswith(ext) for ext in TEMP_EXTENSIONS):
                try: os.remove(os.path.join(root, f))
                except Exception: pass

def get_browser_opts(browser_name, mode, outdir, quality):
    """Génère les options yt-dlp pour un navigateur donné."""
    uas = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ]
    
    opts = {
        "quiet": True,
        "no_warnings": False,
        "outtmpl": os.path.join(outdir, "%(title)s.%(ext)s"),
        "retries": 10,
        "nocheckcertificate": False, # Sécurité activée
        "windowsfilenames": True,
        "cookiesfrombrowser": (browser_name,), 
        "http_headers": {
            "User-Agent": random.choice(uas),
            "Accept-Language": "fr-FR,fr;q=0.9",
        }
    }

    if mode == "MP3":
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality
            }, {"key": "FFmpegMetadata"}]
        })
    else:
        opts.update({
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4"
        })
    return opts

def process_video(url, mode, outdir, quality):
    """Tente le téléchargement avec cascade de navigateurs (Firefox > Edge > Chrome)."""
    start_time = time.time()
    browsers = ["firefox", "edge", "chrome"]
    last_error = ""

    for browser in browsers:
        try:
            ydl_opts = get_browser_opts(browser, mode, outdir, quality)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.cache.remove()
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Vidéo')
                size = (info.get('filesize') or info.get('filesize_approx') or 0) / (1024*1024)
                return time.time() - start_time, f"OK ({browser})", title, size
        except Exception as e:
            last_error = str(e)
            if "Cookie" in last_error or "browser" in last_error:
                continue # Navigateur fermé ou absent, on passe au suivant
            break 

    # Fallback ultime sans cookies
    try:
        fallback_opts = get_browser_opts("firefox", mode, outdir, quality)
        if "cookiesfrombrowser" in fallback_opts: del fallback_opts["cookiesfrombrowser"]
        fallback_opts["format"] = "worst/best"
        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
            ydl.download([url])
        return time.time() - start_time, "OK (Sans Cookies)", "Vidéo", 0
    except Exception as e:
        return 0, f"Erreur finale : {str(e)[:50]}", "Échec", 0

# =========================================================
# INTERFACE STREAMLIT
# =========================================================
st.write("---")
url_input = st.text_input("🔗 URL YouTube", placeholder="Collez le lien ici...")

c1, c2, c3 = st.columns(3)
with c1:
    mode_selection = st.radio("📁 Format de sortie", ["Vidéo MP4", "Audio MP3"], horizontal=True)
with c2:
    mp3_quality = st.selectbox("🎵 Qualité Audio", ["128", "192", "256", "320"], index=3)
with c3:
    max_workers = st.slider("⚡ Téléchargements simultanés", 1, 2, 1)

st.write("---")

if st.button("🚀 DÉMARRER", type="primary", use_container_width=True):
    if not url_input:
        st.warning("Veuillez entrer un lien.")
    else:
        mode = "MP3" if "Audio" in mode_selection else "VIDEO"
        
        with st.spinner("Analyse de la source..."):
            try:
                with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": "in_playlist"}) as ydl:
                    data = ydl.extract_info(url_input, download=False)
                    urls = [e["url"] for e in data.get("entries", []) if e] if "entries" in data else [url_input]
                    folder_name = re.sub(r'[<>:"/\\|?*]', '', data.get("title", "YoutubeHum"))
            except Exception as e:
                st.error(f"Erreur d'analyse : {e}")
                urls = []

        if urls:
            session_path = os.path.join(DEFAULT_DOWNLOAD_DIR, f"{folder_name[:30]}_{datetime.now().strftime('%H%M%S')}")
            os.makedirs(session_path, exist_ok=True)
            
            progress_bar = st.progress(0)
            status_area = st.empty()
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(process_video, u, mode, session_path, mp3_quality): u for u in urls}
                
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    elapsed, msg, title, size = future.result()
                    
                    if msg.startswith("OK"):
                        st.success(f"✅ {title[:60]}... ({size:.1f} MB)")
                        st.session_state.stats["total_downloaded"] += 1
                        st.session_state.stats["total_size_mb"] += size
                    else:
                        st.error(f"❌ {msg}")
                    
                    progress_bar.progress((i + 1) / len(urls))
            
            clean_temp_files(session_path)
            st.balloons()
            st.markdown(f"### 🎉 Terminé ! \n Dossier : `{session_path}`")
            if st.button("📂 Ouvrir le dossier"):
                os.startfile(session_path)

# Barre latérale de statistiques
st.sidebar.title("📊 Session")
st.sidebar.metric("Réussis", st.session_state.stats["total_downloaded"])
st.sidebar.metric("Volume", f"{st.session_state.stats['total_size_mb']:.1f} MB")
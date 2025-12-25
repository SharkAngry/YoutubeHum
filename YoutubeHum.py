import os
import time
import yt_dlp
import streamlit as st
import concurrent.futures
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
# Import important pour fixer l'erreur de contexte
from streamlit.runtime.scriptrunner import add_script_run_ctx

# =========================================================
# CONFIG GÉNÉRALE
# =========================================================
st.set_page_config(page_title="YoutubeHum", page_icon="🎧", layout="wide")
# Initialisation des variables de session
if "history" not in st.session_state:
    st.session_state.history = []
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False

# Style minimal
st.markdown("""<style> .main { background-color: #0f1117; color: #e5e7eb; } </style>""", unsafe_allow_html=True)
st.markdown("""<svg width="240" height="40" viewBox="0 0 240 40"><text x="0" y="28" fill="#e5e7eb" font-size="28" font-family="Inter" font-weight="600">YoutubeHum</text></svg>""", unsafe_allow_html=True)

# =========================================================
# FONCTIONS
# =========================================================
def clean_temp_files(directory):
    if not os.path.exists(directory): return
    for f in os.listdir(directory):
        if f.endswith((".jpg", ".png", ".webp", ".part", ".ytdl", ".temp")):
            try: os.remove(os.path.join(directory, f))
            except: pass

def process_video(url, mode, outdir, quality, use_aria2):
    # NOTE: On ne touche plus à st.session_state ici pour éviter le crash
    start = time.time()
    ydl_opts = {
        "quiet": True, "no_warnings": True,
        "outtmpl": os.path.join(outdir, "%(title)s.%(ext)s"),
        "ignoreerrors": True,
        "nocheckcertificate": True,
    }

    if mode == "MP3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": quality},
                {"key": "FFmpegMetadata"}, {"key": "EmbedThumbnail"},
            ],
            "writethumbnail": True,
        })
    else:
        ydl_opts.update({
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
            "merge_output_format": "mp4",
            "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}, {"key": "FFmpegMetadata"}],
        })

    if use_aria2:
        ydl_opts["external_downloader"] = "aria2c"
        ydl_opts["external_downloader_args"] = ["-x", "16", "-s", "16", "-k", "1M"]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return time.time() - start, "OK"
    except Exception as e:
        return 0, str(e)

def estimate_remaining(times, total, completed):
    if not times: return "—"
    avg = sum(times) / len(times)
    remaining = avg * (total - completed)
    return time.strftime("%M:%S", time.gmtime(remaining))

# =========================================================
# INTERFACE
# =========================================================
st.markdown("### 1. Source")
url_input = st.text_input("Lien YouTube", placeholder="https://...")

st.markdown("### 2. Format & Réglages")
col_sel, col_opt = st.columns(2)
with col_sel:
    mode_selection = st.radio("Format :", ["Vidéo MP4", "Audio MP3"], horizontal=True)
with col_opt:
    with st.expander("Options avancées"):
        quality = st.selectbox("Qualité MP3", ["128", "192", "256", "320"], index=1)
        max_parallel = st.slider("Simultanés", 1, 10, 4)
        use_aria2 = st.checkbox("Accélération Aria2")

st.markdown("### 3. Lancer")
c1, c2 = st.columns([3, 1])
start_btn = c1.button("DÉMARRER LE TÉLÉCHARGEMENT", use_container_width=True, type="primary")

if c2.button("ANNULER", use_container_width=True):
    st.session_state.stop_requested = True
    st.rerun()

# =========================================================
# TRAITEMENT
# =========================================================
if start_btn and url_input:
    st.session_state.stop_requested = False
    mode = "MP3" if "Audio" in mode_selection else "VIDEO"
    
    with st.spinner("Analyse de la source…"):
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": False}) as ydl:
                info = ydl.extract_info(url_input, download=False)
                urls = [e["webpage_url"] for e in info["entries"] if e] if "entries" in info else [url_input]
        except Exception as e:
            st.error(f"Erreur : {e}")
            urls = []

    if urls:
        base_dir = os.path.expanduser("~/Downloads")
        session_dir = os.path.join(base_dir, f"YoutubeHum_{datetime.now().strftime('%H%M%S')}")
        os.makedirs(session_dir, exist_ok=True)

        progress = st.progress(0)
        status = st.empty()
        times, completed, total = [], 0, len(urls)

        # On utilise le ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            # On prépare les tâches
            futures = {executor.submit(process_video, u, mode, session_dir, quality, use_aria2): u for u in urls}
            
            # Attachement du contexte Streamlit à chaque thread pour éviter les warnings
            for thread in executor._threads:
                add_script_run_ctx(thread)

            for future in concurrent.futures.as_completed(futures):
                # ICI on vérifie l'annulation (dans le thread principal, là où c'est autorisé)
                if st.session_state.stop_requested:
                    status.error("🛑 Annulation en cours... Veuillez patienter.")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                
                try:
                    res_time, res_status = future.result()
                    if res_status == "OK":
                        times.append(res_time)
                    completed += 1
                    progress.progress(completed / total)
                    status.info(f"⏳ {completed}/{total} — Temps restant : {estimate_remaining(times, total, completed)}")
                except Exception as e:
                    pass

        if st.session_state.stop_requested:
            st.warning("Téléchargement annulé.")
        else:
            clean_temp_files(session_dir)
            st.session_state.history.append({"date": datetime.now().strftime("%d/%m %H:%M"), "mode": mode, "count": completed, "path": session_dir})
            st.success(f"Fini ! Dossier : {session_dir}")
            st.balloons()
        
        clean_temp_files(session_dir)

# Historique
if st.session_state.history:
    st.markdown("---")
    st.markdown("### Historique de la session")
    for h in reversed(st.session_state.history):
        st.markdown(f"📅 **{h['date']}** | 📥 **{h['mode']}** | 📁 `{h['path']}`")
import os
import time
import yt_dlp
import streamlit as st
import concurrent.futures
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# =========================================================
# CONFIGURATION GÉNÉRALE
# =========================================================
st.set_page_config(
    page_title="YoutubeHum", 
    page_icon="🎧", 
    layout="wide"
)

# Constantes
DEFAULT_DOWNLOAD_DIR = os.path.expanduser("~/Downloads")
TEMP_FILE_EXTENSIONS = (".jpg", ".png", ".webp", ".part", ".ytdl", ".temp")
DOWNLOAD_TIMEOUT = 300  # 5 minutes par vidéo

# Initialisation des variables de session
if "history" not in st.session_state:
    st.session_state.history = []
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "stats" not in st.session_state:
    st.session_state.stats = {"total_downloaded": 0, "total_failed": 0}

# Style CSS amélioré
st.markdown("""
<style>
    .main { 
        background-color: #0f1117; 
        color: #e5e7eb; 
    }
    .stButton button {
        font-weight: 600;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #1e3a2e;
        border-left: 4px solid #10b981;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #3a1e1e;
        border-left: 4px solid #ef4444;
    }
</style>
""", unsafe_allow_html=True)

# Logo
LOGO_WIDTH = 240
LOGO_HEIGHT = 40
TEXT_Y_POSITION = 28

st.markdown(f"""
<svg width="{LOGO_WIDTH}" height="{LOGO_HEIGHT}" viewBox="0 0 {LOGO_WIDTH} {LOGO_HEIGHT}">
  <text x="0" y="{TEXT_Y_POSITION}" fill="#e5e7eb" font-size="28" font-family="Inter" font-weight="600">
    YoutubeHum
  </text>
</svg>
""", unsafe_allow_html=True)

# =========================================================
# FONCTIONS UTILITAIRES
# =========================================================
def clean_temp_files(directory):
    """Nettoie les fichiers temporaires du répertoire."""
    if not os.path.exists(directory):
        return
    
    cleaned_count = 0
    for f in os.listdir(directory):
        if f.endswith(TEMP_FILE_EXTENSIONS):
            try:
                os.remove(os.path.join(directory, f))
                cleaned_count += 1
            except Exception:
                pass
    return cleaned_count

def validate_youtube_url(url):
    """Valide qu'une URL est bien un lien YouTube."""
    youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com']
    return any(domain in url.lower() for domain in youtube_domains)

def format_time(seconds):
    """Formate un temps en secondes en format lisible."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def estimate_remaining(times, total, completed):
    """Estime le temps restant basé sur les téléchargements précédents."""
    if not times or completed >= total:
        return "—"
    avg = sum(times) / len(times)
    remaining = avg * (total - completed)
    return format_time(remaining)

def process_video(url, mode, outdir, quality, use_aria2):
    """
    Télécharge une vidéo YouTube avec extraction des métadonnées.
    
    Returns:
        tuple: (temps_écoulé, statut, titre_vidéo, taille_fichier_mb, durée_secondes)
    """
    start = time.time()
    
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": os.path.join(outdir, "%(title)s.%(ext)s"),
        "ignoreerrors": True,
        "nocheckcertificate": True,
        "socket_timeout": 30,
    }

    if mode == "MP3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality
                },
                {"key": "FFmpegMetadata"},
                {"key": "EmbedThumbnail"},
            ],
            "writethumbnail": True,
        })
    else:
        ydl_opts.update({
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
            "merge_output_format": "mp4",
            "postprocessors": [
                {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"},
                {"key": "FFmpegMetadata"}
            ],
        })

    if use_aria2:
        ydl_opts["external_downloader"] = "aria2c"
        ydl_opts["external_downloader_args"] = [
            "-x", "16", "-s", "16", "-k", "1M"
        ]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extraction des infos AVANT téléchargement (amélioration)
            info = ydl.extract_info(url, download=False)
            
            # Récupération sécurisée des métadonnées
            title = info.get('title', 'Titre inconnu')[:100]  # Limite à 100 caractères
            duration = info.get('duration', 0)  # Durée en secondes
            filesize = info.get('filesize', 0) or info.get('filesize_approx', 0)  # Taille estimée
            
            # Téléchargement
            ydl.download([url])
        
        elapsed = time.time() - start
        filesize_mb = filesize / (1024 * 1024) if filesize else 0
        
        return elapsed, "OK", title, filesize_mb, duration
    
    except Exception as e:
        error_msg = str(e)
        # Simplification du message d'erreur pour l'affichage
        if "Video unavailable" in error_msg:
            error_msg = "Vidéo non disponible"
        elif "Private video" in error_msg:
            error_msg = "Vidéo privée"
        elif "copyright" in error_msg.lower():
            error_msg = "Problème de droits d'auteur"
        
        return 0, f"ERREUR: {error_msg}", "Échec", 0, 0

# =========================================================
# INTERFACE PRINCIPALE
# =========================================================
st.markdown("### 1. Source")

col_url, col_validate = st.columns([5, 1])
with col_url:
    url_input = st.text_input(
        "Lien YouTube", 
        placeholder="https://www.youtube.com/watch?v=... ou playlist",
        label_visibility="collapsed"
    )

# Validation du lien
is_valid_url = validate_youtube_url(url_input) if url_input else False
if url_input and not is_valid_url:
    st.error("⚠️ Ce ne semble pas être un lien YouTube valide")

st.markdown("### 2. Format & Réglages")
col_sel, col_opt = st.columns(2)

with col_sel:
    mode_selection = st.radio(
        "Format :", 
        ["Vidéo MP4", "Audio MP3"], 
        horizontal=True
    )

with col_opt:
    with st.expander("⚙️ Options avancées"):
        quality = st.selectbox(
            "Qualité MP3", 
            ["128", "192", "256", "320"], 
            index=1,
            help="Plus la qualité est élevée, plus le fichier sera volumineux"
        )
        max_parallel = st.slider(
            "Téléchargements simultanés", 
            1, 10, 4,
            help="Augmenter peut accélérer mais consomme plus de ressources"
        )
        use_aria2 = st.checkbox(
            "Accélération Aria2",
            help="Nécessite aria2c installé sur votre système"
        )
        custom_dir = st.text_input(
            "Dossier personnalisé (optionnel)",
            placeholder=DEFAULT_DOWNLOAD_DIR
        )

st.markdown("### 3. Lancer le téléchargement")
c1, c2 = st.columns([3, 1])

start_btn = c1.button(
    "🚀 DÉMARRER LE TÉLÉCHARGEMENT", 
    use_container_width=True, 
    type="primary",
    disabled=not is_valid_url
)

if c2.button("🛑 ANNULER", use_container_width=True):
    st.session_state.stop_requested = True
    st.rerun()

# =========================================================
# TRAITEMENT DES TÉLÉCHARGEMENTS
# =========================================================
if start_btn and url_input and is_valid_url:
    st.session_state.stop_requested = False
    mode = "MP3" if "Audio" in mode_selection else "VIDEO"
    
    # Analyse de la source
    with st.spinner("🔍 Analyse de la source..."):
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": False}) as ydl:
                info = ydl.extract_info(url_input, download=False)
                
                if "entries" in info:
                    urls = [e["webpage_url"] for e in info["entries"] if e]
                    st.info(f"📋 Playlist détectée : {len(urls)} vidéo(s)")
                else:
                    urls = [url_input]
                    st.info(f"📹 Vidéo unique détectée")
        
        except Exception as e:
            st.error(f"❌ Erreur lors de l'analyse : {e}")
            urls = []

    if urls:
        # Création du dossier de destination
        base_dir = custom_dir if custom_dir else DEFAULT_DOWNLOAD_DIR
        session_dir = os.path.join(
            base_dir, 
            f"YoutubeHum_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        os.makedirs(session_dir, exist_ok=True)

        # Initialisation des indicateurs
        progress = st.progress(0)
        status = st.empty()
        details = st.empty()
        
        times = []
        completed = 0
        failed = 0
        total = len(urls)
        successful_titles = []
        total_size_mb = 0
        total_duration = 0

        # Téléchargement avec ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = {
                executor.submit(process_video, u, mode, session_dir, quality, use_aria2): u 
                for u in urls
            }

            for future in concurrent.futures.as_completed(futures):
                # Vérification d'annulation
                if st.session_state.stop_requested:
                    status.error("🛑 Annulation en cours... Veuillez patienter.")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                
                try:
                    res_time, res_status, title, size_mb, duration = future.result(timeout=DOWNLOAD_TIMEOUT)
                    
                    if res_status == "OK":
                        times.append(res_time)
                        successful_titles.append(title)
                        total_size_mb += size_mb
                        total_duration += duration
                        details.success(f"✅ {title[:60]}... ({format_time(res_time)})")
                    else:
                        failed += 1
                        details.warning(f"⚠️ {title}: {res_status}")
                    
                    completed += 1
                    progress.progress(completed / total)
                    
                    # Affichage enrichi avec taille et durée
                    avg_speed = total_size_mb / sum(times) if times and sum(times) > 0 else 0
                    status.info(
                        f"⏳ Progression : {completed}/{total} "
                        f"(✅ {len(times)} | ❌ {failed}) "
                        f"— Temps restant : {estimate_remaining(times, total, completed)} "
                        f"— Vitesse moy. : {avg_speed:.1f} MB/s"
                    )
                
                except concurrent.futures.TimeoutError:
                    failed += 1
                    completed += 1
                    details.warning("⏱️ Timeout dépassé pour une vidéo")
                
                except Exception as e:
                    failed += 1
                    completed += 1

        # Nettoyage et résumé
        clean_temp_files(session_dir)
        
        if st.session_state.stop_requested:
            st.warning("⚠️ Téléchargement annulé par l'utilisateur.")
        else:
            # Mise à jour des statistiques
            st.session_state.stats["total_downloaded"] += len(times)
            st.session_state.stats["total_failed"] += failed
            
            # Ajout à l'historique
            st.session_state.history.append({
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "mode": mode,
                "count": len(times),
                "failed": failed,
                "path": session_dir,
                "avg_time": sum(times) / len(times) if times else 0,
                "total_size_mb": total_size_mb,
                "total_duration": total_duration
            })
            
            # Affichage du résumé enrichi
            if len(times) > 0:
                avg_time = sum(times) / len(times)
                avg_speed = total_size_mb / sum(times) if sum(times) > 0 else 0
                
                st.markdown(f"""
                <div class="success-box">
                    <h3>✅ Téléchargement terminé !</h3>
                    <p><strong>📁 Dossier :</strong> <code>{session_dir}</code></p>
                    <p><strong>✅ Réussis :</strong> {len(times)} / {total}</p>
                    <p><strong>⏱️ Temps moyen :</strong> {format_time(avg_time)}</p>
                    <p><strong>💾 Taille totale :</strong> {total_size_mb:.1f} MB</p>
                    <p><strong>🎬 Durée totale :</strong> {format_time(total_duration)}</p>
                    <p><strong>⚡ Vitesse moyenne :</strong> {avg_speed:.2f} MB/s</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.balloons()
                
                # Bouton pour ouvrir le dossier (Windows/Mac/Linux)
                if st.button("📂 Ouvrir le dossier"):
                    import subprocess
                    import platform
                    
                    if platform.system() == "Windows":
                        os.startfile(session_dir)
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.Popen(["open", session_dir])
                    else:  # Linux
                        subprocess.Popen(["xdg-open", session_dir])
            else:
                st.error("❌ Aucun téléchargement réussi.")

# =========================================================
# HISTORIQUE ET STATISTIQUES
# =========================================================
if st.session_state.history:
    st.markdown("---")
    st.markdown("### 📊 Historique de la session")
    
    # Statistiques globales
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("Total téléchargés", st.session_state.stats["total_downloaded"])
    with col_stat2:
        st.metric("Total échoués", st.session_state.stats["total_failed"])
    with col_stat3:
        success_rate = (
            st.session_state.stats["total_downloaded"] / 
            (st.session_state.stats["total_downloaded"] + st.session_state.stats["total_failed"]) * 100
            if (st.session_state.stats["total_downloaded"] + st.session_state.stats["total_failed"]) > 0
            else 0
        )
        st.metric("Taux de succès", f"{success_rate:.1f}%")
    
    st.markdown("#### Détails")
    for h in reversed(st.session_state.history):
        with st.expander(f"📅 {h['date']} — {h['mode']} — {h['count']} fichier(s)"):
            st.markdown(f"**Chemin :** `{h['path']}`")
            st.markdown(f"**Réussis :** {h['count']} | **Échoués :** {h['failed']}")
            if h['avg_time'] > 0:
                st.markdown(f"**Temps moyen :** {format_time(h['avg_time'])}")
            if h.get('total_size_mb', 0) > 0:
                st.markdown(f"**Taille totale :** {h['total_size_mb']:.1f} MB")
            if h.get('total_duration', 0) > 0:
                st.markdown(f"**Durée totale :** {format_time(h['total_duration'])}")
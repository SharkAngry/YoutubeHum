import os
import time
import yt_dlp
import streamlit as st
import concurrent.futures
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys

# =========================================================
# CONFIGURATION OPTIMISÉE WINDOWS
# =========================================================
st.set_page_config(
    page_title="YoutubeHum", 
    page_icon="🎧", 
    layout="wide"
)

# Constantes optimisées pour Windows
DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
TEMP_FILE_EXTENSIONS = (".jpg", ".png", ".webp", ".part", ".ytdl", ".temp", ".f*")
DOWNLOAD_TIMEOUT = 600  # 10 minutes par vidéo
CHUNK_SIZE = 10485760  # 10MB chunks pour Windows

# Configuration pour éviter les problèmes de certificats SSL sur Windows
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''

# Initialisation des variables de session
if "history" not in st.session_state:
    st.session_state.history = []
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "stats" not in st.session_state:
    st.session_state.stats = {"total_downloaded": 0, "total_failed": 0, "total_size_mb": 0}

# Style CSS amélioré
st.markdown("""
<style>
    .main { 
        background-color: #0f1117; 
        color: #e5e7eb; 
    }
    .stButton button {
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .success-box {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #1e3a2e;
        border-left: 4px solid #10b981;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #3a1e1e;
        border-left: 4px solid #ef4444;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #1e293b;
        border-left: 4px solid #3b82f6;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Logo
st.markdown("""
<svg width="240" height="40" viewBox="0 0 240 40">
  <text x="0" y="28" fill="#e5e7eb" font-size="28" font-family="Inter" font-weight="600">
    YoutubeHum
  </text>
  <text x="190" y="28" fill="#10b981" font-size="14" font-family="Inter" font-weight="400">
    v2.0
  </text>
</svg>
""", unsafe_allow_html=True)

# =========================================================
# FONCTIONS UTILITAIRES OPTIMISÉES WINDOWS
# =========================================================
def check_dependencies():
    """Vérifie les dépendances système pour Windows."""
    issues = []
    
    # Vérifier FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], 
                      capture_output=True, 
                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    except FileNotFoundError:
        issues.append("FFmpeg non détecté")
    
    # Vérifier aria2c (optionnel)
    try:
        subprocess.run(["aria2c", "--version"], 
                      capture_output=True,
                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    except FileNotFoundError:
        issues.append("aria2c non installé (optionnel pour accélération)")
    
    return issues

def clean_temp_files(directory):
    """Nettoie les fichiers temporaires du répertoire (optimisé Windows)."""
    if not os.path.exists(directory):
        return 0
    
    cleaned_count = 0
    for root, dirs, files in os.walk(directory):
        for f in files:
            if any(f.endswith(ext) for ext in TEMP_FILE_EXTENSIONS) or f.startswith('.'):
                try:
                    file_path = os.path.join(root, f)
                    os.remove(file_path)
                    cleaned_count += 1
                except Exception:
                    pass
    return cleaned_count

def validate_youtube_url(url):
    """Valide qu'une URL est bien un lien YouTube."""
    if not url:
        return False
    youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com', 'youtube-nocookie.com']
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

def get_optimal_format(mode, quality):
    """
    Retourne le format optimal pour éviter l'erreur 22 d'aria2.
    L'erreur 22 survient souvent avec des formats fragmentés.
    """
    if mode == "MP3":
        # Pour l'audio, on utilise des formats non fragmentés
        return "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
    else:
        # Pour la vidéo, on évite les formats fragmentés qui causent l'erreur 22
        # On préfère les formats progressifs (non-DASH)
        return "bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/bestvideo+bestaudio/best"

def process_video(url, mode, outdir, quality, use_aria2, use_proxy=False):
    """
    Télécharge une vidéo YouTube avec optimisations Windows.
    
    Returns:
        tuple: (temps_écoulé, statut, titre_vidéo, taille_fichier_mb, durée_secondes)
    """
    start = time.time()
    
    # Options de base optimisées pour Windows
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": os.path.join(outdir, "%(title)s.%(ext)s"),
        "ignoreerrors": False,  # On veut capturer les vraies erreurs
        "nocheckcertificate": True,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 10,
        "file_access_retries": 3,
        "http_chunk_size": CHUNK_SIZE,
        # Optimisations Windows
        "windowsfilenames": True,  # Noms de fichiers compatibles Windows
        "restrictfilenames": False,
        "trim_file_name": 200,  # Limite la longueur des noms
        # Performance
        "concurrent_fragment_downloads": 4,
        "buffersize": 16384,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-us,en;q=0.5",
            "Sec-Fetch-Mode": "navigate",
        }
    }

    if mode == "MP3":
        ydl_opts.update({
            "format": get_optimal_format("MP3", quality),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality
                },
                {"key": "FFmpegMetadata"},
                {"key": "EmbedThumbnail", "already_have_thumbnail": False},
            ],
            "writethumbnail": True,
            "embedthumbnail": True,
        })
    else:
        ydl_opts.update({
            "format": get_optimal_format("VIDEO", quality),
            "merge_output_format": "mp4",
            "postprocessors": [
                {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"},
                {"key": "FFmpegMetadata"}
            ],
        })

    # Configuration aria2c OPTIMISÉE pour éviter l'erreur 22
    if use_aria2:
        # On n'utilise aria2 QUE pour les gros fichiers non fragmentés
        ydl_opts["external_downloader"] = "aria2c"
        ydl_opts["external_downloader_args"] = [
            "--min-split-size=1M",
            "--max-connection-per-server=8",  # Réduit de 16 à 8 pour plus de stabilité
            "--split=8",  # Réduit de 16 à 8
            "--max-concurrent-downloads=4",
            "--continue=true",
            "--max-tries=5",
            "--retry-wait=3",
            "--timeout=60",
            "--connect-timeout=30",
            "--file-allocation=none",  # Important pour Windows
            "--allow-overwrite=true",
            "--auto-file-renaming=false",
        ]
    else:
        # Utiliser le downloader natif de yt-dlp (plus stable)
        ydl_opts["http_chunk_size"] = CHUNK_SIZE

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extraction des infos AVANT téléchargement
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return 0, "ERREUR: Impossible d'extraire les informations", "Échec", 0, 0
            
            # Récupération sécurisée des métadonnées
            title = info.get('title', 'Titre inconnu')
            # Nettoyer le titre pour Windows
            title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_', '.'))[:100]
            duration = info.get('duration', 0)
            filesize = info.get('filesize', 0) or info.get('filesize_approx', 0)
            
            # Vérifier si c'est un format fragmenté (cause de l'erreur 22)
            is_fragmented = info.get('protocol', '') in ('m3u8', 'm3u8_native', 'http_dash_segments')
            
            # Si fragmenté et aria2 activé, désactiver aria2 pour ce fichier
            if is_fragmented and use_aria2:
                ydl_opts.pop('external_downloader', None)
                ydl_opts.pop('external_downloader_args', None)
            
            # Téléchargement
            ydl.download([url])
        
        elapsed = time.time() - start
        filesize_mb = filesize / (1024 * 1024) if filesize else 0
        
        return elapsed, "OK", title, filesize_mb, duration
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        # Détection des erreurs spécifiques
        if "HTTP Error 403" in error_msg:
            error_msg = "Accès refusé (erreur 403)"
        elif "HTTP Error 404" in error_msg:
            error_msg = "Vidéo introuvable (erreur 404)"
        elif "ERROR 22" in error_msg or "error code 22" in error_msg.lower():
            error_msg = "Erreur aria2 (format incompatible)"
        elif "Video unavailable" in error_msg:
            error_msg = "Vidéo non disponible"
        elif "Private video" in error_msg:
            error_msg = "Vidéo privée"
        elif "copyright" in error_msg.lower():
            error_msg = "Problème de droits d'auteur"
        
        return 0, f"ERREUR: {error_msg}", "Échec", 0, 0
    
    except Exception as e:
        return 0, f"ERREUR: {str(e)[:100]}", "Échec", 0, 0

# =========================================================
# INTERFACE PRINCIPALE
# =========================================================

# Vérification des dépendances
with st.expander("ℹ️ État du système", expanded=False):
    issues = check_dependencies()
    if issues:
        st.warning(f"⚠️ Dépendances manquantes : {', '.join(issues)}")
        st.markdown("""
        **Installation rapide :**
        - **FFmpeg** : [Télécharger](https://www.gyan.dev/ffmpeg/builds/) et ajouter au PATH
        - **aria2c** : `winget install aria2.aria2` ou [Télécharger](https://github.com/aria2/aria2/releases)
        """)
    else:
        st.success("✅ Toutes les dépendances sont installées")

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
            index=2,
            help="Qualité recommandée : 256 kbps"
        )
        
        max_parallel = st.slider(
            "Téléchargements simultanés", 
            1, 8, 3,
            help="Recommandé : 3-4 pour éviter les blocages"
        )
        
        use_aria2 = st.checkbox(
            "Accélération aria2c",
            value=False,
            help="⚠️ Peut causer l'erreur 22 sur certains formats. Désactivé par défaut."
        )
        
        st.markdown("---")
        
        custom_dir = st.text_input(
            "Dossier personnalisé (optionnel)",
            placeholder=DEFAULT_DOWNLOAD_DIR
        )
        
        if custom_dir and not os.path.exists(custom_dir):
            st.warning("⚠️ Ce dossier n'existe pas. Il sera créé.")

st.markdown("### 3. Lancer le téléchargement")
c1, c2, c3 = st.columns([2, 1, 1])

start_btn = c1.button(
    "🚀 DÉMARRER", 
    use_container_width=True, 
    type="primary",
    disabled=not is_valid_url
)

if c2.button("🛑 ANNULER", use_container_width=True):
    st.session_state.stop_requested = True
    st.rerun()

if c3.button("🧹 Nettoyer", use_container_width=True):
    st.session_state.history = []
    st.session_state.stats = {"total_downloaded": 0, "total_failed": 0, "total_size_mb": 0}
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
            with yt_dlp.YoutubeDL({
                "quiet": True, 
                "no_warnings": True,
                "extract_flat": "in_playlist"  # Optimisation pour les playlists
            }) as ydl:
                info = ydl.extract_info(url_input, download=False)
                
                if "entries" in info:
                    # Filtrer les entrées None
                    urls = [e["url"] if "url" in e else e["webpage_url"] 
                           for e in info["entries"] if e]
                    st.info(f"📋 Playlist détectée : {len(urls)} vidéo(s)")
                else:
                    urls = [url_input]
                    st.info(f"📹 Vidéo unique détectée : {info.get('title', 'Sans titre')}")
        
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
        
        try:
            os.makedirs(session_dir, exist_ok=True)
        except Exception as e:
            st.error(f"❌ Impossible de créer le dossier : {e}")
            st.stop()

        # Initialisation des indicateurs
        progress = st.progress(0, text="Démarrage...")
        status = st.empty()
        details = st.container()
        
        times = []
        completed = 0
        failed = 0
        total = len(urls)
        successful_titles = []
        total_size_mb = 0
        total_duration = 0
        failed_urls = []

        # Téléchargement avec ThreadPoolExecutor
        start_time = time.time()
        
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
                        
                        with details:
                            st.success(f"✅ {title[:70]}... ({format_time(res_time)}, {size_mb:.1f} MB)")
                    else:
                        failed += 1
                        failed_urls.append((title, res_status))
                        
                        with details:
                            st.warning(f"⚠️ {title[:50]}... — {res_status}")
                    
                    completed += 1
                    progress.progress(completed / total, text=f"Progression : {completed}/{total}")
                    
                    # Affichage enrichi avec statistiques en temps réel
                    elapsed_total = time.time() - start_time
                    avg_speed = total_size_mb / elapsed_total if elapsed_total > 0 else 0
                    
                    status.info(
                        f"⏳ **{completed}/{total}** téléchargés "
                        f"(✅ {len(times)} | ❌ {failed}) — "
                        f"Restant : **{estimate_remaining(times, total, completed)}** — "
                        f"Vitesse : **{avg_speed:.2f} MB/s**"
                    )
                
                except concurrent.futures.TimeoutError:
                    failed += 1
                    completed += 1
                    with details:
                        st.error("⏱️ Timeout dépassé pour une vidéo")
                
                except Exception as e:
                    failed += 1
                    completed += 1
                    with details:
                        st.error(f"❌ Erreur inattendue : {str(e)[:100]}")

        # Nettoyage et résumé
        cleaned = clean_temp_files(session_dir)
        
        if st.session_state.stop_requested:
            st.warning("⚠️ Téléchargement annulé par l'utilisateur.")
        else:
            # Mise à jour des statistiques
            st.session_state.stats["total_downloaded"] += len(times)
            st.session_state.stats["total_failed"] += failed
            st.session_state.stats["total_size_mb"] += total_size_mb
            
            # Ajout à l'historique
            st.session_state.history.append({
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "mode": mode,
                "count": len(times),
                "failed": failed,
                "path": session_dir,
                "avg_time": sum(times) / len(times) if times else 0,
                "total_size_mb": total_size_mb,
                "total_duration": total_duration,
                "failed_details": failed_urls
            })
            
            # Affichage du résumé enrichi
            if len(times) > 0:
                total_elapsed = time.time() - start_time
                avg_time = sum(times) / len(times)
                avg_speed = total_size_mb / total_elapsed if total_elapsed > 0 else 0
                
                st.markdown(f"""
                <div class="success-box">
                    <h3>✅ Téléchargement terminé !</h3>
                    <p><strong>📁 Dossier :</strong> <code>{session_dir}</code></p>
                    <p><strong>✅ Réussis :</strong> {len(times)} / {total} ({len(times)/total*100:.1f}%)</p>
                    <p><strong>⏱️ Temps total :</strong> {format_time(total_elapsed)}</p>
                    <p><strong>⚡ Temps moyen/vidéo :</strong> {format_time(avg_time)}</p>
                    <p><strong>💾 Taille totale :</strong> {total_size_mb:.1f} MB</p>
                    <p><strong>🎬 Durée totale :</strong> {format_time(total_duration)}</p>
                    <p><strong>📶 Vitesse moyenne :</strong> {avg_speed:.2f} MB/s</p>
                    <p><strong>🧹 Fichiers temporaires nettoyés :</strong> {cleaned}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.balloons()
                
                # Bouton pour ouvrir le dossier (Windows)
                if st.button("📂 Ouvrir le dossier", type="secondary"):
                    try:
                        os.startfile(session_dir)
                    except Exception as e:
                        st.error(f"Impossible d'ouvrir le dossier : {e}")
            else:
                st.error("❌ Aucun téléchargement réussi.")
            
            # Afficher les échecs détaillés
            if failed_urls:
                with st.expander(f"⚠️ Voir les {len(failed_urls)} échec(s)"):
                    for title, error in failed_urls:
                        st.markdown(f"- **{title}** : {error}")

# =========================================================
# HISTORIQUE ET STATISTIQUES
# =========================================================
if st.session_state.history:
    st.markdown("---")
    st.markdown("### 📊 Historique de la session")
    
    # Statistiques globales
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    with col_stat1:
        st.metric("✅ Total téléchargés", st.session_state.stats["total_downloaded"])
    with col_stat2:
        st.metric("❌ Total échoués", st.session_state.stats["total_failed"])
    with col_stat3:
        total_attempts = st.session_state.stats["total_downloaded"] + st.session_state.stats["total_failed"]
        success_rate = (
            st.session_state.stats["total_downloaded"] / total_attempts * 100
            if total_attempts > 0 else 0
        )
        st.metric("📈 Taux de succès", f"{success_rate:.1f}%")
    with col_stat4:
        st.metric("💾 Volume total", f"{st.session_state.stats['total_size_mb']:.1f} MB")
    
    st.markdown("#### 📋 Détails des téléchargements")
    for idx, h in enumerate(reversed(st.session_state.history)):
        with st.expander(
            f"📅 {h['date']} — {h['mode']} — "
            f"{h['count']} réussi(s) / {h['count'] + h['failed']} total"
        ):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**📁 Chemin :** `{h['path']}`")
                st.markdown(f"**✅ Réussis :** {h['count']}")
                st.markdown(f"**❌ Échoués :** {h['failed']}")
            
            with col2:
                if h['avg_time'] > 0:
                    st.markdown(f"**⏱️ Temps moyen :** {format_time(h['avg_time'])}")
                if h.get('total_size_mb', 0) > 0:
                    st.markdown(f"**💾 Taille totale :** {h['total_size_mb']:.1f} MB")
                if h.get('total_duration', 0) > 0:
                    st.markdown(f"**🎬 Durée totale :** {format_time(h['total_duration'])}")
            
            if h.get('failed_details'):
                st.markdown("**Échecs détaillés :**")
                for title, error in h['failed_details']:
                    st.markdown(f"- {title[:50]}... : {error}")
            
            if st.button(f"📂 Ouvrir", key=f"open_{idx}"):
                try:
                    os.startfile(h['path'])
                except Exception as e:
                    st.error(f"Impossible d'ouvrir : {e}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6b7280; font-size: 0.875rem;">
    YoutubeHum v2.0 - Optimisé pour Windows | 
    Utilise yt-dlp, FFmpeg et aria2c
</div>
""", unsafe_allow_html=True)
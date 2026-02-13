@echo off
title YoutubeHum Ultimate Launcher
setlocal

:: Couleurs pour le terminal (Bleu)
color 0B

echo =========================================================
echo            YOUTUBEHUM ULTIMATE - CHARGEMENT
echo =========================================================
echo.

:: 1. Vérification/Installation des dépendances critiques
echo [1/3] Verification des modules (yt-dlp, streamlit, certifi)...
python -m pip install -U yt-dlp streamlit certifi --quiet

:: 2. Nettoyage du cache Python pour eviter les erreurs de lancement
echo [2/3] Nettoyage du cache...
set PYTHONDONTWRITEBYTECODE=1

:: 3. Lancement de l'application
echo [3/3] Lancement de l'interface Streamlit...
echo.
echo ---------------------------------------------------------
echo SI L'INTERFACE NE S'OUVRE PAS : 
echo Copiez l'adresse URL qui va s'afficher ci-dessous 
echo (souvent http://localhost:8501) dans votre navigateur.
echo ---------------------------------------------------------
echo.

:: Utilisation de python -m pour contourner l'erreur de PATH
python -m streamlit run YoutubeHum.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERREUR] L'application ne s'est pas lancee correctement.
    echo Verifiez que le fichier YoutubeHum.py est dans le meme dossier.
    pause
)

pause
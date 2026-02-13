@echo off
title YoutubeHum Launcher
color 0A

echo =========================================
echo        YoutubeHum - Demarrage
echo =========================================
echo.

:: Aller dans le dossier du script
cd /d "%~dp0"

:: Vérifier Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python n'est pas installé ou pas dans le PATH.
    pause
    exit /b
)

:: Création venv si absent
if not exist ".venv" (
    echo Creation environnement virtuel...
    python -m venv .venv
)

:: Activation venv
call .venv\Scripts\activate

:: Upgrade pip silencieux
python -m pip install --upgrade pip >nul

:: Installer dépendances si besoin
pip install -U yt-dlp streamlit certifi >nul

:: Vérifier FFmpeg
where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ATTENTION : FFmpeg non detecte.
    echo Telecharge-le et ajoute-le au PATH.
    echo.
)

:: Lancer application
echo.
echo Lancement de l'application...
echo.
streamlit run YoutubeHum.py

echo.
echo Application fermee.
pause

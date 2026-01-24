@echo off
title YoutubeHum Launcher
echo ----------------------------------------------
echo      Lancement de YoutubeHum (Python 3.14)
echo ----------------------------------------------

:: Vérifie si Streamlit est installé
python -m streamlit --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Streamlit n'est pas installe sur cette version de Python.
    echo Installation des dependances en cours...
    python -m pip install -r requirements.txt
)

:: Lance l'application
python -m streamlit run YoutubeHum.py

pause
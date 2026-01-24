@echo off
chcp 65001 >nul
title YoutubeHum Launcher v2.0
color 0A

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║       YoutubeHum - Launcher Windows                 ║
echo ║       Optimisé pour Python 3.14                     ║
echo ╚══════════════════════════════════════════════════════╝
echo.

:: Vérification de Python
echo [1/4] Vérification de Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installé ou pas dans le PATH
    echo.
    echo Veuillez installer Python depuis https://www.python.org/
    echo N'oubliez pas de cocher "Add Python to PATH" lors de l'installation
    pause
    exit /b 1
)

python --version
echo.

:: Vérification de Streamlit
echo [2/4] Vérification de Streamlit...
python -m streamlit --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Streamlit n'est pas installé
    echo [INFO] Installation des dépendances en cours...
    echo.
    
    if exist requirements.txt (
        python -m pip install --upgrade pip
        python -m pip install -r requirements.txt
        
        if %errorlevel% neq 0 (
            echo [ERREUR] Échec de l'installation des dépendances
            pause
            exit /b 1
        )
        echo [OK] Dépendances installées avec succès
    ) else (
        echo [ERREUR] Fichier requirements.txt introuvable
        echo Installation manuelle de Streamlit et yt-dlp...
        python -m pip install streamlit yt-dlp
    )
) else (
    echo [OK] Streamlit est déjà installé
)
echo.

:: Vérification de yt-dlp
echo [3/4] Vérification de yt-dlp...
python -c "import yt_dlp" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installation de yt-dlp...
    python -m pip install yt-dlp
) else (
    echo [OK] yt-dlp est installé
)
echo.

:: Vérification de FFmpeg (optionnel mais recommandé)
echo [4/4] Vérification de FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVERTISSEMENT] FFmpeg n'est pas détecté
    echo FFmpeg est nécessaire pour la conversion audio/vidéo
    echo Téléchargez-le sur: https://www.gyan.dev/ffmpeg/builds/
    echo.
) else (
    echo [OK] FFmpeg est installé
)
echo.

:: Vérification du fichier Python
if not exist YoutubeHum.py (
    echo [ERREUR] Le fichier YoutubeHum.py est introuvable dans ce dossier
    echo Assurez-vous que le fichier est présent: %CD%
    pause
    exit /b 1
)

:: Lancement de l'application
echo ══════════════════════════════════════════════════════
echo Lancement de YoutubeHum...
echo ══════════════════════════════════════════════════════
echo.
echo Une fenêtre de navigateur va s'ouvrir automatiquement
echo Pour arrêter l'application, appuyez sur Ctrl+C
echo.

:: Lance Streamlit avec des paramètres optimisés
python -m streamlit run YoutubeHum.py ^
    --server.headless=false ^
    --browser.gatherUsageStats=false ^
    --server.fileWatcherType=none

:: Si Streamlit se ferme
echo.
echo ══════════════════════════════════════════════════════
echo YoutubeHum s'est arrêté
echo ══════════════════════════════════════════════════════
pause
```

## 🎯 Améliorations apportées :

### ✅ **Robustesse**
1. **Vérification de Python** : S'assure que Python est installé ET dans le PATH
2. **Gestion d'erreurs** : Vérifie chaque étape et affiche des messages clairs
3. **Vérification du fichier** : S'assure que `YoutubeHum.py` existe
4. **Codes de sortie** : Utilise `exit /b 1` pour signaler les erreurs

### ✅ **Meilleures pratiques**
1. **chcp 65001** : Support des caractères UTF-8 (emojis, accents)
2. **color 0A** : Interface verte sur fond noir (style Matrix)
3. **Mise à jour de pip** : Évite les problèmes d'installation
4. **Paramètres Streamlit** : Optimisés pour Windows

### ✅ **Vérifications complètes**
- ✅ Python installé
- ✅ Streamlit installé
- ✅ yt-dlp installé
- ✅ FFmpeg présent (avec avertissement si absent)
- ✅ Fichier YoutubeHum.py présent

### ✅ **Interface améliorée**
```
╔══════════════════════════════════════════════════════╗
║       YoutubeHum - Launcher Windows                 ║
║       Optimisé pour Python 3.14                     ║
╚══════════════════════════════════════════════════════╝

[1/4] Vérification de Python...
[2/4] Vérification de Streamlit...
[3/4] Vérification de yt-dlp...
[4/4] Vérification de FFmpeg...
# 🎧 YoutubeHum — Le Downloader \*\*

YoutubeHum est une interface **Streamlit** élégante et rapide pour télécharger des vidéos YouTube en **MP4** ou les convertir en **MP3** avec métadonnées et miniatures intégrées.

## 🚀 Fonctionnalités

- **Mode Turbo** : Support de `aria2` pour saturer votre bande passante.
- **Parallélisme** : Téléchargez plusieurs vidéos d'une playlist simultanément.
- **Conversion MP4/MP3** : Gestion automatique via FFmpeg pour une compatibilité maximale.
- **Historique** : Gardez une trace de vos téléchargements de la session.
- **Interface Pro** : Design sombre et épuré avec estimation du temps restant.

## 🛠️ Installation

1. **Prérequis** :
   --- Installez [FFmpeg](https://ffmpeg.org/download.html) (indispensable pour la conversion).
   De preferences, installez en ligne de commande :
   Intaller le gestionnaire de paquets _choco_ avec la commande :
   Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   Ensuite ferme ton terminal et rouvre-le (Important).
   Maintenant, essaie : choco install ffmpeg
   Ensuite fais : ffmpeg -version
   Si tu vois du texte s'afficher avec un numéro de version au lieu d'une erreur, c'est gagné !
   --- Installez Python genre l'interpreteur.
2. **Dépendances** :

```bash
pip install -r requirements.txt
```

3. **Utilisation** :
   Lancez l'application avec :

```bash
streamlit run YoutubeHum.py
```

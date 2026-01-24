# 🎧 YoutubeHum — Downloader YouTube rapide

Interface **Streamlit** simple et efficace pour télécharger des vidéos YouTube en **MP4** ou les convertir en **MP3** avec métadonnées et miniatures.

## 🚀 Fonctionnalités

- **Téléchargements parallèles** : Plusieurs vidéos en même temps (jusqu'à 8).
- **MP4/MP3** : Vidéo ou audio, au choix.
- **Support playlists** : Balance un lien de playlist et ça télécharge tout.
- **Mode turbo (aria2c)** : Accélération optionnelle (mais parfois buggy).
- **Stats en temps réel** : Vitesse, progression, temps restant.
- **Historique** : Garde une trace de tout ce que t'as DL dans la session.
- **Auto-nettoyage** : Vire les fichiers temporaires automatiquement.

## 🛠️ Installation

### 1. Prérequis

**FFmpeg** (obligatoire) :

- Ouvre PowerShell en **admin**
- Installe Chocolatey :

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

- Ferme et rouvre ton terminal
- Installe FFmpeg : `choco install ffmpeg`
- Vérifie : `ffmpeg -version`

**aria2c** (optionnel, pour aller plus vite) :

```powershell
winget install aria2.aria2
```

**Python** : Genre 3.10+ minimum

### 2. Installation

```bash
git clone https://github.com/TON_USERNAME/YoutubeHum.git
cd YoutubeHum
pip install -r requirements.txt
```

### 3. Lancement

**Facile :** Double-clique sur `launcher.bat`

**Ou en ligne de commande :**

```bash
streamlit run YoutubeHum.py
```

## 📖 Utilisation

1. Colle un lien YouTube (vidéo ou playlist)
2. Choisis MP4 ou MP3
3. Configure les options si tu veux (qualité, simultanés...)
4. Clique sur "DÉMARRER"
5. Regarde la magie opérer ✨

Les fichiers se téléchargent dans `~/Downloads/YoutubeHum_YYYYMMDD_HHMMSS/`

## ⚙️ Options recommandées

| Paramètre   | Valeur   | Pourquoi                                  |
| ----------- | -------- | ----------------------------------------- |
| Qualité MP3 | 256 kbps | Bon compromis qualité/taille              |
| Simultanés  | 3-4      | Plus = plus rapide mais plus instable     |
| aria2c      | OFF      | Marche bien mais peut planter (erreur 22) |

## 🐛 Problèmes courants

**"Python n'est pas reconnu"**
→ Réinstalle Python et coche "Add to PATH"

**Erreur 22 avec aria2**
→ Désactive aria2c dans les options, le downloader de base marche très bien

**FFmpeg pas détecté**
→ Vérifie que `ffmpeg -version` marche dans ton terminal

**Téléchargement bloqué**
→ Réduis le nombre de téléchargements simultanés

## 📦 Fichiers

```
YoutubeHum/
├── YoutubeHum.py          # L'app
├── launcher.bat           # Double-clique et ça lance tout
├── requirements.txt       # Les trucs à installer
└── README.md             # T'es là
```

## 🤝 Contribuer

T'as une idée ? Un bug ? Ouvre une issue ou fais une PR, c'est open source !

## 📝 Licence

MIT — Fais ce que tu veux avec

## 🙏 Merci à

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) pour le téléchargement
- [Streamlit](https://streamlit.io/) pour l'interface
- FFmpeg pour la conversion
- aria2 pour la vitesse (quand ça marche)

---

Fait avec ❤️ par un étudiant qui en avait marre de télécharger une par une

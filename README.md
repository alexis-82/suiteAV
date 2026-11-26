<div align="center">

# suiteAV

**Download audio and video from YouTube and SoundCloud, and convert your music to MP3, from the terminal.**<br>
*Scarica audio e video da YouTube e SoundCloud e converti la tua musica in MP3, dal terminale.*

[![Version](https://img.shields.io/badge/version-4.1.1-blue?style=plastic)](CHANGELOG.md)&nbsp;&nbsp;&nbsp;[![Python](https://img.shields.io/badge/Python-3776AB?style=plastic&logo=python&logoColor=white)](#)&nbsp;&nbsp;&nbsp;[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey?style=plastic)](#)

🇬🇧 [English](#en)&nbsp;&nbsp;·&nbsp;&nbsp;🇮🇹 [Italiano](#it)

</div>

---

<a id="en"></a>
<a id="contents"></a>
## 📑 Contents

- [✨ What it is](#what-it-is)
- [🚀 Installation](#installation)
- [🧭 How to use](#how-to-use)
- [🛟 Troubleshooting](#troubleshooting)
- [📄 License](#license)

---

<a id="what-it-is"></a>
## ✨ What it is

suiteAV is a program you use from the terminal, with simple menus you move through with the arrow keys.

- **Download from YouTube and SoundCloud**: videos in the quality you prefer (up to 360p, 480p, 720p, best quality, MP4), music as high-quality MP3 with its cover, whole albums split into tracks by chapter, or a list of links saved in a text file.
- **Convert your music to MP3**: FLAC, M4A/AAC, WAV, OGG and OPUS files become MP3 at 320 kbps, keeping title, artist, album and cover. You can convert one song or a whole folder.
- **Always know what is happening**: progress bars with speed and time remaining, and a notification when the work is done.

It works on Linux, Windows and macOS, in Italian or English.

<a id="installation"></a>
## 🚀 Installation

**On Windows, the quick way.**

1. Install ffmpeg: open PowerShell and paste:

   ```
   winget install --source winget Gyan.FFmpeg
   ```

2. Download [suiteAV-4.1.1-windows-x64-installer.exe](https://github.com/alexis-82/suiteAV/releases/download/v4.1.1/suiteAV-4.1.1-windows-x64-installer.exe) (from the [4.1.1 release](https://github.com/alexis-82/suiteAV/releases/tag/v4.1.1)) and open it. It installs suiteAV for your user only (no administrator password) and adds it to the Start menu and, if you want, to the desktop.

Windows may show "Windows protected your PC": click **More info** and then **Run anyway**. To update, install the new version over the old one. To uninstall, use **Settings > Apps > Installed apps**.

If you prefer not to install anything, download [suiteAV-4.1.1-windows-x64.zip](https://github.com/alexis-82/suiteAV/releases/download/v4.1.1/suiteAV-4.1.1-windows-x64.zip) instead, extract it wherever you like and open `suiteAV.exe` inside the `suiteAV` folder.

**On Linux and macOS** (or on Windows, if you prefer the terminal) you need two things: **ffmpeg** (the tool that joins and converts audio and video) and **uv** (the tool that installs suiteAV).

**1. Install ffmpeg.**
Open the Terminal and paste the command for your system:

```
Windows:          winget install --source winget Gyan.FFmpeg
macOS:            brew install ffmpeg
Ubuntu / Debian:  sudo apt install ffmpeg
Arch:             sudo pacman -S ffmpeg
Fedora:           sudo dnf install ffmpeg-free
```

**2. Install uv.**
On Windows open PowerShell and paste:

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

On Linux and macOS open the Terminal and paste:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Arch you can install it from the official repositories instead:

```
sudo pacman -S uv
```

Then close the window and open a new one.

**3. Install suiteAV.**
Paste this command:

```
uv tool install git+https://github.com/alexis-82/suiteAV
```

You don't need to install Python yourself: uv takes care of it.

**To update suiteAV** :

```
uv tool upgrade suiteav
```

**On Linux**, to find suiteAV in the applications menu (it opens in a terminal window), paste:

```
suiteav --install-desktop
```

To remove it from the menu:
```
suiteav --uninstall-desktop
```

**Coming from version 3.x?** The new version doesn't use the old folder: you can delete it after moving your old downloads, which are in its `Downloads` folder.

<a id="how-to-use"></a>
## 🧭 How to use

Open the Terminal and type:

```
suiteav
```

- Move with the **arrow keys** and confirm with **Enter**. **Esc** takes you back.
- To download, choose **YouTube / SoundCloud**, pick what you want and paste the link.
- To convert music, choose **Audio conversion (to MP3)** and type (or drag into the window) the file or folder.
- **Ctrl+C** stops what is running and brings you back to the menu.

Your files end up in the **suiteAV** folder inside your system's downloads folder (for example `Downloads/suiteAV`, or `Scaricati/suiteAV` on an Italian Linux system): `Video`, `Audio` and `Converted`. The menu entry **Open downloads folder** opens it for you.

The language follows your system (Italian or English). To change the folder or the language, edit the settings file `config.toml`, which suiteAV creates the first time you start it:

- Windows: `%LOCALAPPDATA%\suiteav\config.toml`
- macOS: `~/Library/Application Support/suiteav/config.toml`
- Linux: `~/.config/suiteav/config.toml`

<a id="troubleshooting"></a>
## 🛟 Troubleshooting

- **"ffmpeg is missing"**: install ffmpeg (step 1 of the installation), then try again. The **Dependencies** screen shows the right command for your system.
- **"JS runtime missing"**: YouTube downloads may fail or offer fewer qualities. Reinstall suiteAV with `uv tool install --reinstall git+https://github.com/alexis-82/suiteAV`.
- **A file was not converted**: the summary at the end lists the files with errors and why. Files that are not audio are simply ignored.
- **No notification on macOS**: on macOS notifications may not appear; downloads and conversions work anyway.

<a id="license"></a>
## 📄 License

suiteAV is free software released under the GNU General Public License version 2. See the [LICENSE](LICENSE) file.

---

<a id="it"></a>
<a id="indice"></a>
## 📑 Indice

- [✨ Cos'è](#cose)
- [🚀 Installazione](#installazione)
- [🧭 Come si usa](#come-si-usa)
- [🛟 Problemi comuni](#problemi-comuni)
- [📄 Licenza](#licenza)

---

<a id="cose"></a>
## ✨ Cos'è

suiteAV è un programma che usi dal terminale, con menu semplici in cui ti muovi con le frecce.

- **Scarica da YouTube e SoundCloud**: video nella qualità che preferisci (fino a 360p, 480p, 720p, migliore qualità, MP4), musica in MP3 di alta qualità con la copertina, album interi divisi in brani per capitolo, oppure un elenco di link salvati in un file di testo.
- **Converte la tua musica in MP3**: i file FLAC, M4A/AAC, WAV, OGG e OPUS diventano MP3 a 320 kbps, mantenendo titolo, artista, album e copertina. Puoi convertire un brano o una cartella intera.
- **Sai sempre cosa sta succedendo**: barre di avanzamento con velocità e tempo rimanente, e una notifica quando il lavoro è finito.

Funziona su Linux, Windows e macOS, in italiano o in inglese.

<a id="installazione"></a>
## 🚀 Installazione

**Su Windows, la via veloce.**

1. Installa ffmpeg: apri PowerShell e incolla:

   ```
   winget install --source winget Gyan.FFmpeg
   ```

2. Scarica [suiteAV-4.1.1-windows-x64-installer.exe](https://github.com/alexis-82/suiteAV/releases/download/v4.1.1/suiteAV-4.1.1-windows-x64-installer.exe) (dalla [release 4.1.1](https://github.com/alexis-82/suiteAV/releases/tag/v4.1.1)) e aprilo. Installa suiteAV solo per il tuo utente (senza password di amministratore) e lo aggiunge al menu Start e, se vuoi, al desktop.

Windows può mostrare "PC protetto da Windows": fai clic su **Ulteriori informazioni** e poi su **Esegui comunque**. Per aggiornare, installa la nuova versione sopra la vecchia. Per disinstallare, usa **Impostazioni > App > App installate**.

Se preferisci non installare nulla, scarica invece [suiteAV-4.1.1-windows-x64.zip](https://github.com/alexis-82/suiteAV/releases/download/v4.1.1/suiteAV-4.1.1-windows-x64.zip), estrailo dove preferisci e apri `suiteAV.exe` nella cartella `suiteAV`.

**Su Linux e macOS** (o su Windows, se preferisci il terminale) ti servono due cose: **ffmpeg** (lo strumento che unisce e converte audio e video) e **uv** (lo strumento che installa suiteAV).

**1. Installa ffmpeg.**
Apri il Terminale e incolla il comando per il tuo sistema:

```
Windows:          winget install --source winget Gyan.FFmpeg
macOS:            brew install ffmpeg
Ubuntu / Debian:  sudo apt install ffmpeg
Arch:             sudo pacman -S ffmpeg
Fedora:           sudo dnf install ffmpeg-free
```

**2. Installa uv.**
Su Windows apri PowerShell e incolla:

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Su Linux e macOS apri il Terminale e incolla:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Su Arch puoi installarlo invece dai repository ufficiali:

```
sudo pacman -S uv
```

Poi chiudi la finestra e aprine una nuova.

**3. Installa suiteAV.**
Incolla questo comando:

```
uv tool install git+https://github.com/alexis-82/suiteAV
```

Non devi installare Python: ci pensa uv.

**Per aggiornare suiteAV** :

```
uv tool upgrade suiteav
```

**Su Linux**, per trovare suiteAV nel menu delle applicazioni (si apre in una finestra del terminale), incolla:

```
suiteav --install-desktop
```

Per toglierlo dal menu:
```
suiteav --uninstall-desktop
```

**Arrivi dalla versione 3.x?** La nuova versione non usa la vecchia cartella: puoi cancellarla dopo aver spostato i vecchi download, che si trovano nella sua cartella `Downloads`.

<a id="come-si-usa"></a>
## 🧭 Come si usa

Apri il Terminale e scrivi:

```
suiteav
```

- Muoviti con le **frecce** e conferma con **Invio**. **Esc** ti riporta indietro.
- Per scaricare, scegli **YouTube / SoundCloud**, scegli cosa vuoi e incolla il link.
- Per convertire la musica, scegli **Conversione audio (in MP3)** e scrivi (o trascina nella finestra) il file o la cartella.
- **Ctrl+C** ferma quello che sta succedendo e ti riporta al menu.

I tuoi file finiscono nella cartella **suiteAV** dentro la cartella dei download del sistema (per esempio `Downloads/suiteAV`, oppure `Scaricati/suiteAV` su Linux in italiano): `Video`, `Audio` e `Converted`. La voce **Apri la cartella dei download** la apre per te.

La lingua segue quella del sistema (italiano o inglese). Per cambiare la cartella o la lingua, modifica il file delle impostazioni `config.toml`, che suiteAV crea al primo avvio:

- Windows: `%LOCALAPPDATA%\suiteav\config.toml`
- macOS: `~/Library/Application Support/suiteav/config.toml`
- Linux: `~/.config/suiteav/config.toml`

<a id="problemi-comuni"></a>
## 🛟 Problemi comuni

- **"ffmpeg mancante"**: installa ffmpeg (passo 1 dell'installazione) e riprova. La schermata **Dipendenze** mostra il comando giusto per il tuo sistema.
- **"Runtime JS mancante"**: i download da YouTube possono fallire o avere meno qualità. Reinstalla suiteAV con `uv tool install --reinstall git+https://github.com/alexis-82/suiteAV`.
- **Un file non è stato convertito**: il riepilogo finale elenca i file con errori e il motivo. I file che non sono audio vengono semplicemente ignorati.
- **Nessuna notifica su macOS**: su macOS le notifiche possono non comparire; download e conversioni funzionano comunque.

<a id="licenza"></a>
## 📄 Licenza

suiteAV è software libero distribuito con la GNU General Public License versione 2. Vedi il file [LICENSE](LICENSE).

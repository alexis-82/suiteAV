# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.0.0] - 2026-11-26

### Added

- One version for Linux, Windows and macOS, installed with a single command.
- Interactive menus: choose with the arrow keys and Enter (the cursor stops at the first and last entry), go back with Esc.
- Live progress bars with size, speed and time remaining for downloads and conversions.
- Audio conversion to MP3 (320 kbps) from FLAC, M4A/AAC, WAV, OGG and OPUS, for a single file or a whole folder, keeping title, artist, album and cover art. Files already converted are skipped.
- Status bar with suiteAV and yt-dlp versions, available updates, ffmpeg and the JavaScript runtime needed by YouTube.
- Dependencies screen that tells you the exact command to install ffmpeg on your system.
- Desktop notification when a download or conversion finishes (best effort on macOS).
- Settings file to choose the download folder and the language (Italian or English, automatic by default).
- On Linux, `suiteav --install-desktop` adds suiteAV to the applications menu (no administrator password needed); `suiteav --uninstall-desktop` removes it.
- "Video conversion" menu entry, not available yet.

### Changed

- Files are saved in a `suiteAV` folder inside your system's downloads folder, whatever its name in your language (`Audio`, `Video`, `Converted`), instead of the program folder.
- The 360p, 480p and 720p entries now download the best quality up to that resolution.
- The Updates screen only checks whether a new version exists; it no longer downloads or installs anything.
- Quitting closes suiteAV only, not the terminal window.

### Removed

- The "Installation packages" menu: suiteAV no longer installs system packages; it tells you what is missing and how to install it.

### Fixed

- The "with metadata" download entries now really save the metadata.
- The fixed-quality entries no longer fail on videos without the old YouTube formats.
- Ctrl+C stops the current operation and returns to the menu.

### Security

- Links and file names are never passed to a system shell.

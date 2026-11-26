import sys
import tomllib

from suiteav import __version__


def main() -> None:
    if "--version" in sys.argv[1:]:
        print(f"suiteAV {__version__}")
        return
    if "--install-desktop" in sys.argv[1:] or "--uninstall-desktop" in sys.argv[1:]:
        _desktop("--install-desktop" in sys.argv[1:])
        return

    from suiteav import app
    from suiteav.core import config, i18n
    from suiteav.core import platform as plat

    try:
        cfg = config.load()
    except tomllib.TOMLDecodeError as e:
        path = plat.config_dir() / config.CONFIG_FILENAME
        print(f"suiteAV: {path} non valido / invalid: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        # Es. download_dir su un disco scollegato o senza permessi: messaggio, non traceback
        path = plat.config_dir() / config.CONFIG_FILENAME
        print(f"suiteAV: cartella non accessibile / folder not accessible: {e}\n"
              f"  config: {path}", file=sys.stderr)
        sys.exit(1)

    i18n.setup(cfg.language)
    try:
        app.run(cfg)
    except KeyboardInterrupt:
        pass


def _desktop(install: bool) -> None:
    from suiteav.core import desktop
    from suiteav.core import platform as plat

    if plat.os_name() != "linux":
        print("suiteAV: solo Linux / Linux only", file=sys.stderr)
        sys.exit(1)
    try:
        if install:
            path = desktop.install()
            print(f"suiteAV: lanciatore creato / launcher created: {path}")
        elif desktop.uninstall():
            print("suiteAV: lanciatore rimosso / launcher removed")
        else:
            print("suiteAV: nessun lanciatore da rimuovere / no launcher to remove")
    except OSError as e:
        print(f"suiteAV: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

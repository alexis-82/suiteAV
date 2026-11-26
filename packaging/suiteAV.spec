# PyInstaller: build a cartella (niente --onefile: meno falsi positivi degli antivirus
# e nessuna estrazione in %TEMP% a ogni avvio).
#   pip install ".[build]"
#   pyinstaller packaging/suiteAV.spec
# Risultato: dist/suiteAV/ con suiteAV(.exe), deno(.exe) e _internal/.
import os
import shutil
import sysconfig

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = (collect_data_files("suiteav")            # traduzioni .mo, icona
         + collect_data_files("yt_dlp_ejs")       # script JS per YouTube
         + collect_data_files("desktop_notifier"))
hiddenimports = (collect_submodules("rich._unicode_data")  # importati per nome a runtime
                 + collect_submodules("winrt"))            # backend notifiche Windows

a = Analysis(
    [os.path.join(SPECPATH, "entry.py")],
    datas=datas,
    hiddenimports=hiddenimports,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="suiteAV",
    console=True,
    icon=os.path.join(SPECPATH, "suiteav.ico"),  # quadrata, la stessa dell'installer
)
COLLECT(exe, a.binaries, a.datas, name="suiteAV")

# deno accanto all'eseguibile, non in _internal/: yt-dlp congelato lo cerca nella
# cartella dell'exe, e così fa suiteav.core.deps.find_deno.
deno = os.path.join(sysconfig.get_path("scripts"), "deno" + (sysconfig.get_config_var("EXE") or ""))
if not os.path.isfile(deno):
    raise SystemExit(f"deno non trovato in {deno}: installare suiteAV con pip install '.[build]'")
shutil.copy2(deno, os.path.join(DISTPATH, "suiteAV"))

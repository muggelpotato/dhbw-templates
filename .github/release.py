import subprocess
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

bau = subprocess.run([sys.executable, REPO / "word" / "bau" / "bau.py", "--ohne-logos"], stdout=subprocess.PIPE, text=True, check=True)
with tempfile.TemporaryDirectory() as ordner:
    zips = []
    for dotx in map(Path, bau.stdout.splitlines()):
        zips.append(Path(ordner, dotx.stem + ".zip"))
        with zipfile.ZipFile(zips[-1], "w", zipfile.ZIP_DEFLATED) as paket:
            for datei in (dotx, *(REPO / "zitierstil").iterdir()):
                paket.write(datei, datei.name)
    subprocess.run(["gh", "release", "create", date.today().isoformat(), *zips, "--generate-notes"], cwd=REPO, check=True)

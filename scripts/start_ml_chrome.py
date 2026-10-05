import subprocess
import time
from pathlib import Path

import requests


CDP_URL = "http://127.0.0.1:9222"
CHROME_PATH = "/opt/google/chrome/chrome"

PROJECT_DIR = Path(__file__).resolve().parent.parent
PROFILE_DIR = PROJECT_DIR / "data" / "chrome_debug_profile"


def cdp_available() -> bool:
    try:
        response = requests.get(
            f"{CDP_URL}/json/version",
            timeout=2,
        )
        return response.ok
    except requests.RequestException:
        return False


def start_chrome() -> None:
    print("Chrome CDP não encontrado. Iniciando...")

    subprocess.Popen(
        [
            CHROME_PATH,
            f"--user-data-dir={PROFILE_DIR}",
            "--profile-directory=Default",
            "--remote-debugging-port=9222",
            "--no-first-run",
            "--no-default-browser-check",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def ensure_chrome() -> None:
    if cdp_available():
        print("Chrome CDP já está disponível.")
        return

    start_chrome()

    for tentativa in range(30):
        if cdp_available():
            print("Chrome CDP disponível.")
            return

        time.sleep(1)

    raise RuntimeError(
        "Chrome foi iniciado, mas o CDP não ficou disponível "
        "na porta 9222."
    )


if __name__ == "__main__":
    ensure_chrome()
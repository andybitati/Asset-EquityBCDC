import os
import subprocess
import threading
import time
import webbrowser

import uvicorn

from backend.app.config import runtime_dir
from backend.app.main import app


def resolve_runtime_path(value: str | None) -> str | None:
    if not value:
        return None
    if os.path.isabs(value):
        return value
    return os.path.join(runtime_dir(), value)


def https_config() -> dict:
    certfile = resolve_runtime_path(os.getenv("ASSET_EQUITY_SSL_CERTFILE"))
    keyfile = resolve_runtime_path(os.getenv("ASSET_EQUITY_SSL_KEYFILE"))
    if not certfile and not keyfile:
        return {}
    if not certfile or not keyfile:
        raise RuntimeError(
            "HTTPS incomplet: ASSET_EQUITY_SSL_CERTFILE et ASSET_EQUITY_SSL_KEYFILE doivent être définis ensemble."
        )
    if not os.path.isfile(certfile):
        raise RuntimeError(f"Certificat HTTPS introuvable: {certfile}")
    if not os.path.isfile(keyfile):
        raise RuntimeError(f"Clé privée HTTPS introuvable: {keyfile}")
    return {"ssl_certfile": certfile, "ssl_keyfile": keyfile}


def public_scheme() -> str:
    return "https" if https_config() else "http"


def public_url() -> str:
    configured_url = os.getenv("ASSET_EQUITY_PUBLIC_URL")
    if configured_url:
        return configured_url.rstrip("/")
    port = int(os.getenv("ASSET_EQUITY_PORT", "48620"))
    return f"{public_scheme()}://127.0.0.1:{port}"


def open_preferred_browser(url: str) -> None:
    if os.name == "nt":
        candidates = [
            os.path.join(os.getenv("ProgramFiles", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.getenv("ProgramFiles(x86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.getenv("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.getenv("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ]
        for browser_path in candidates:
            if browser_path and os.path.isfile(browser_path):
                subprocess.Popen([browser_path, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
    webbrowser.open(url)


def open_browser():
    time.sleep(2)
    open_preferred_browser(public_url())


if __name__ == "__main__":
    host = os.getenv("ASSET_EQUITY_HOST", "127.0.0.1")
    port = int(os.getenv("ASSET_EQUITY_PORT", "48620"))
    if os.getenv("ASSET_EQUITY_OPEN_BROWSER", "true").lower() == "true":
        threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host=host, port=port, reload=False, **https_config())

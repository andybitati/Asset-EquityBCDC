import os
import threading
import time
import webbrowser

import uvicorn

from backend.app.main import app


def open_browser():
    time.sleep(2)
    port = int(os.getenv("ASSET_EQUITY_PORT", "48620"))
    webbrowser.open(f"http://127.0.0.1:{port}")


if __name__ == "__main__":
    host = os.getenv("ASSET_EQUITY_HOST", "127.0.0.1")
    port = int(os.getenv("ASSET_EQUITY_PORT", "48620"))
    if os.getenv("ASSET_EQUITY_OPEN_BROWSER", "true").lower() == "true":
        threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host=host, port=port, reload=False)

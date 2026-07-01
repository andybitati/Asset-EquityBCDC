import base64
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import struct
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "overleaf-captures"
RUNTIME_DIR = Path(tempfile.gettempdir()) / "asset_equity_overleaf_capture_runtime"
DB_PATH = RUNTIME_DIR / "asset_equity_capture.db"
EDGE_PATHS = [
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
]
BACKEND_URL = "http://127.0.0.1:48620"
CDP_PORT = 9222


def wait_for_http(url, timeout=30):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return True
        except Exception as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"Service indisponible: {url} ({last_error})")


def sha256_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def seed_database():
    deadline = time.time() + 20
    required_tables = {"sessions", "users", "movements", "materials", "entry_serial_numbers"}
    while time.time() < deadline:
        conn = sqlite3.connect(DB_PATH)
        try:
            tables = {
                row[0]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if required_tables.issubset(tables):
                break
        finally:
            conn.close()
        time.sleep(0.3)
    else:
        raise RuntimeError("La base SQLite de capture n'a pas été initialisée correctement.")

    conn = sqlite3.connect(DB_PATH)
    now = datetime.utcnow()
    conn.execute("DELETE FROM sessions")
    conn.execute("DELETE FROM audit_logs")
    conn.execute("DELETE FROM entry_serial_numbers")
    conn.execute("DELETE FROM movements")
    conn.execute("DELETE FROM materials")
    conn.execute("DELETE FROM users")
    users = [
        ("admin", "Admin Equity", sha256_password("StrongPassword123!"), "admin", "/avatar-admin.svg", 1),
        ("manager", "Manager IT Assets", sha256_password("Manager2026!"), "manager", "/avatar-manager.svg", 1),
        ("auditor", "Auditeur IT", sha256_password("Auditor2026!"), "auditor", "/avatar-auditor.svg", 1),
        ("user", "Utilisateur BCDC", sha256_password("Password2026!"), "user", "/avatar-user-gold.svg", 1),
    ]
    conn.executemany(
        "INSERT INTO users (username, display_name, password_hash, role, photo_url, is_active, last_credentials_changed_at, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(u, d, p, r, photo, active, now, now, now) for u, d, p, r, photo, active in users],
    )

    materials = [
        ("Laptop ProBook", None, None, "Lot de laptops ProBook pour affectation"),
        ("Moniteur", None, None, "Moniteurs disponibles au dépôt"),
        ("Souris avec fil", None, None, "Accessoires utilisateurs"),
        ("Clavier", None, None, "Accessoires utilisateurs"),
        ("Switch 24 ports", None, None, "Équipement réseau"),
        ("Routeur", None, None, "Équipement réseau"),
    ]
    material_ids = {}
    for item in materials:
        cursor = conn.execute(
            "INSERT INTO materials (equipment_type, serial_number, model, description, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (*item, now, now),
        )
        material_ids[item[0]] = cursor.lastrowid

    movements = [
        ("Entrée", "Laptop ProBook", 5, None, None, None, None, "admin", "Réception lot laptops ProBook"),
        ("Entrée", "Moniteur", 8, None, None, None, None, "admin", "Réception moniteurs"),
        ("Entrée", "Souris avec fil", 25, None, None, None, None, "user", "Réapprovisionnement accessoires"),
        ("Entrée", "Clavier", 18, None, None, None, None, "user", "Réapprovisionnement accessoires"),
        ("Entrée", "Switch 24 ports", 2, None, None, None, None, "admin", "Équipement réseau reçu"),
        ("Entrée", "Routeur", 2, None, None, None, None, "admin", "Équipement réseau reçu"),
        ("Sortie", "Laptop ProBook", 1, "PB-2026-001", "HP ProBook 450 G10", "Direction des opérations", "Joel Ilunga", "user", "Affectation poste utilisateur"),
        ("Sortie", "Moniteur", 1, "MON-2026-004", "HP E24 G5", "Digital Banking", "Bénédicte Nzimbu", "user", "Remplacement écran"),
        ("Sortie", "Souris avec fil", 6, None, None, "Dépôt IT", "Support utilisateurs", "manager", "Distribution accessoires"),
        ("Sortie", "Clavier", 4, None, None, "Dépôt IT", "Support utilisateurs", "manager", "Distribution accessoires"),
        ("Sortie", "Switch 24 ports", 1, "SW-IT-024-01", "Cisco CBS250", "Salle réseau", "Nolly Mashika", "admin", "Installation réseau"),
    ]
    movement_ids = []
    for index, movement in enumerate(movements):
        movement_type, equipment_type, quantity, serial, model, destination, taken_by, actor, notes = movement
        ts = now - timedelta(days=len(movements) - index)
        cursor = conn.execute(
            "INSERT INTO movements (material_id, timestamp, movement_type, equipment_type, quantity, serial_number, model, destination, taken_by, initiated_by, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (material_ids[equipment_type], ts, movement_type, equipment_type, quantity, serial, model, destination, taken_by, actor, notes),
        )
        movement_ids.append(cursor.lastrowid)

    serials = [
        ("Laptop ProBook", "PB-2026-001", "exited", movement_ids[0], movement_ids[6]),
        ("Laptop ProBook", "PB-2026-002", "in_stock", movement_ids[0], None),
        ("Laptop ProBook", "PB-2026-003", "in_stock", movement_ids[0], None),
        ("Laptop ProBook", "PB-2026-004", "in_stock", movement_ids[0], None),
        ("Laptop ProBook", "PB-2026-005", "in_stock", movement_ids[0], None),
        ("Moniteur", "MON-2026-004", "exited", movement_ids[1], movement_ids[7]),
        ("Moniteur", "MON-2026-005", "in_stock", movement_ids[1], None),
        ("Switch 24 ports", "SW-IT-024-01", "exited", movement_ids[4], movement_ids[10]),
        ("Switch 24 ports", "SW-IT-024-02", "in_stock", movement_ids[4], None),
    ]
    for equipment_type, serial, status, entry_id, exit_id in serials:
        conn.execute(
            "INSERT INTO entry_serial_numbers (material_id, entry_movement_id, exit_movement_id, equipment_type, serial_number, normalized_serial_number, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (material_ids[equipment_type], entry_id, exit_id, equipment_type, serial, serial.casefold(), status, now, now),
        )

    audit_items = [
        ("admin", "create_entry", "movement", str(movement_ids[0]), "Réception laptops"),
        ("user", "create_exit", "movement", str(movement_ids[6]), "Sortie laptop ProBook"),
        ("manager", "manager_review_required_exit", "movement", str(movement_ids[8]), "Sortie proche réserve"),
        ("admin", "export_movements_csv", "export", None, "Export CSV"),
    ]
    for actor, action, entity_type, entity_id, value in audit_items:
        conn.execute(
            "INSERT INTO audit_logs (actor_username, action, entity_type, entity_id, new_value, ip_address, user_agent, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (actor, action, entity_type, entity_id, value, "127.0.0.1", "capture-script", now),
        )

    conn.commit()
    conn.close()


def start_backend():
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
    env["STORAGE_DIR"] = str(RUNTIME_DIR / "storage")
    env["CORS_ORIGINS"] = f"{BACKEND_URL},http://localhost:48620"
    log_path = OUT_DIR / "_backend.log"
    handle = open(log_path, "w", encoding="utf-8")
    process = subprocess.Popen(
        [str(ROOT / "venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "48620"],
        cwd=ROOT,
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    wait_for_http(f"{BACKEND_URL}/health", timeout=45)
    return process, handle


def find_edge():
    for candidate in EDGE_PATHS:
        if candidate.exists():
            return candidate
    raise RuntimeError("Microsoft Edge est introuvable.")


class CdpClient:
    def __init__(self, ws_url):
        prefix = "ws://"
        if not ws_url.startswith(prefix):
            raise ValueError(ws_url)
        host_port, path = ws_url[len(prefix):].split("/", 1)
        host, port = host_port.split(":", 1)
        self.host = host
        self.port = int(port)
        self.path = "/" + path
        self.sock = socket.create_connection((self.host, self.port), timeout=10)
        self.next_id = 0
        self._handshake()

    def _handshake(self):
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = self.sock.recv(4096)
        if b"101" not in response.split(b"\r\n", 1)[0]:
            raise RuntimeError(f"Échec WebSocket CDP: {response[:120]!r}")

    def _send_frame(self, payload):
        data = payload.encode("utf-8")
        header = bytearray([0x81])
        length = len(data)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(data))
        self.sock.sendall(header + masked)

    def _recv_exact(self, count):
        chunks = bytearray()
        while len(chunks) < count:
            chunk = self.sock.recv(count - len(chunks))
            if not chunk:
                raise RuntimeError("Connexion CDP fermée.")
            chunks.extend(chunk)
        return bytes(chunks)

    def _recv_frame(self):
        first, second = self._recv_exact(2)
        opcode = first & 0x0F
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(8))[0]
        masked = bool(second & 0x80)
        mask = self._recv_exact(4) if masked else b""
        payload = self._recv_exact(length)
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        if opcode == 0x8:
            raise RuntimeError("CDP a fermé la connexion.")
        if opcode == 0x9:
            return self._recv_frame()
        return payload.decode("utf-8")

    def command(self, method, params=None):
        self.next_id += 1
        message_id = self.next_id
        self._send_frame(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        while True:
            payload = json.loads(self._recv_frame())
            if payload.get("id") == message_id:
                if "error" in payload:
                    raise RuntimeError(payload["error"])
                return payload.get("result", {})

    def evaluate(self, expression, await_promise=True):
        return self.command("Runtime.evaluate", {
            "expression": expression,
            "awaitPromise": await_promise,
            "returnByValue": True,
        })

    def screenshot(self, path):
        result = self.command("Page.captureScreenshot", {
            "format": "png",
            "fromSurface": True,
            "captureBeyondViewport": False,
        })
        path.write_bytes(base64.b64decode(result["data"]))

    def close(self):
        self.sock.close()


def new_cdp_page(url):
    request = urllib.request.Request(f"http://127.0.0.1:{CDP_PORT}/json/new?{url}", method="PUT")
    with urllib.request.urlopen(request, timeout=10) as response:
        target = json.loads(response.read().decode("utf-8"))
    return CdpClient(target["webSocketDebuggerUrl"])


def wait_js(client, expression, timeout=20):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            result = client.evaluate(f"Boolean({expression})", await_promise=False)
            if result.get("result", {}).get("value"):
                return
        except Exception as exc:
            last_error = exc
        time.sleep(0.2)
    raise RuntimeError(f"Timeout en attendant: {expression} ({last_error})")


def click_nav(client, label, expected_selector):
    client.evaluate(f"""
    (() => {{
      const buttons = Array.from(document.querySelectorAll('button'));
      const button = buttons.find(item => item.textContent.trim() === {json.dumps(label)});
      if (!button) throw new Error('Bouton introuvable: {label}');
      button.click();
    }})()
    """)
    wait_js(client, f"document.querySelector({json.dumps(expected_selector)})")
    time.sleep(0.8)


def capture_screens():
    edge = find_edge()
    user_data = RUNTIME_DIR / "edge-profile"
    if user_data.exists():
        shutil.rmtree(user_data)
    edge_process = subprocess.Popen([
        str(edge),
        "--headless=new",
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={user_data}",
        "--disable-gpu",
        "--window-size=1600,1000",
        "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for_http(f"http://127.0.0.1:{CDP_PORT}/json/version", timeout=20)
        client = new_cdp_page(BACKEND_URL)
        try:
            client.command("Page.enable")
            client.command("Runtime.enable")
            client.command("Emulation.setDeviceMetricsOverride", {
                "width": 1600,
                "height": 1000,
                "deviceScaleFactor": 1,
                "mobile": False,
            })
            wait_js(client, "document.querySelector('.auth-page')")
            time.sleep(1)
            client.screenshot(OUT_DIR / "01_connexion.png")

            client.evaluate("""
            (() => {
              const setValue = (element, value) => {
                const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                setter.call(element, value);
                element.dispatchEvent(new Event('input', { bubbles: true }));
              };
              const inputs = document.querySelectorAll('input');
              setValue(inputs[0], 'admin');
              setValue(inputs[1], 'StrongPassword123!');
              document.querySelector('form').requestSubmit();
            })()
            """)
            wait_js(client, "document.querySelector('.dashboard-page')")
            time.sleep(2)
            client.screenshot(OUT_DIR / "02_tableau_de_bord.png")

            pages = [
                ("Stock", ".inventory-page", "03_gestion_entrees_sorties.png"),
                ("Registre séries", ".page", "04_registre_series.png"),
                ("Politiques stock", ".page", "05_politiques_stock.png"),
                ("Mouvements", ".page", "06_mouvements.png"),
                ("Export CSV", ".page", "07_export_csv.png"),
                ("Audit", ".page", "08_audit.png"),
                ("Profil", ".page", "09_profil.png"),
            ]
            for label, selector, filename in pages:
                click_nav(client, label, selector)
                client.screenshot(OUT_DIR / filename)
        finally:
            client.close()
    finally:
        edge_process.terminate()
        try:
            edge_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            edge_process.kill()


def copy_static_assets():
    assets = {
        "assets-equity-logo.png": ROOT / "frontend" / "public" / "assets-equity-logo.png",
        "equity-bank-logo.png": ROOT / "frontend" / "public" / "equity-bank-logo.png",
        "approuvee.jpg": ROOT / "frontend" / "public" / "approuvee.jpg",
        "refusee.jpg": ROOT / "frontend" / "public" / "refusee.jpg",
    }
    for output_name, source in assets.items():
        if source.exists():
            shutil.copy2(source, OUT_DIR / output_name)


def write_notes():
    screenshots = [
        ("01_connexion.png", "Écran de connexion de l'application Assets Equity BCDC"),
        ("02_tableau_de_bord.png", "Tableau de bord de suivi du stock informatique"),
        ("03_gestion_entrees_sorties.png", "Écran de gestion des entrées et sorties de matériel"),
        ("04_registre_series.png", "Registre des numéros de série"),
        ("05_politiques_stock.png", "Paramétrage des politiques de stock"),
        ("06_mouvements.png", "Historique des mouvements de stock"),
        ("07_export_csv.png", "Écran d'export des mouvements"),
        ("08_audit.png", "Journal d'audit des actions sensibles"),
        ("09_profil.png", "Profil utilisateur"),
    ]
    readme = [
        "# Captures pour Overleaf",
        "",
        "Dossier prêt à téléverser dans Overleaf. Les captures ont été générées depuis l'application locale avec une base SQLite de démonstration.",
        "",
        "## Captures",
        "",
    ]
    latex = ["% Exemples d'insertion dans le rapport LaTeX", ""]
    for filename, caption in screenshots:
        readme.append(f"- `{filename}` : {caption}.")
        latex.extend([
            "\\begin{figure}[h!]",
            "\\centering",
            f"\\includegraphics[width=0.95\\textwidth]{{captures/{filename}}}",
            f"\\caption{{{caption}}}",
            "\\end{figure}",
            "",
        ])
    readme.extend([
        "",
        "## Images statiques incluses",
        "",
        "- `assets-equity-logo.png`",
        "- `equity-bank-logo.png`",
        "- `approuvee.jpg`",
        "- `refusee.jpg`",
        "",
        "Dans Overleaf, tu peux créer un dossier `captures` et y déposer ces fichiers.",
    ])
    (OUT_DIR / "README.md").write_text("\n".join(readme), encoding="utf-8")
    (OUT_DIR / "latex_snippets.tex").write_text("\n".join(latex), encoding="utf-8")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.png"):
        old.unlink()
    if DB_PATH.exists():
        DB_PATH.unlink()

    backend, backend_log = start_backend()
    try:
        seed_database()
        capture_screens()
        copy_static_assets()
        write_notes()
    finally:
        backend.terminate()
        try:
            backend.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend.kill()
        backend_log.close()

    print(f"Captures prêtes: {OUT_DIR}")


if __name__ == "__main__":
    main()

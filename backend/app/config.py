import os
import sys

from dotenv import load_dotenv


BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_FILE = os.path.join(BACKEND_DIR, ".env")
APP_DATA_DIR_NAME = "Assets Equity BCDC"


def runtime_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()


def writable_runtime_dir() -> str:
    if getattr(sys, "frozen", False):
        candidate_roots = [
            os.getenv("LOCALAPPDATA"),
            os.getenv("PROGRAMDATA"),
            os.path.expanduser("~"),
        ]
        for base_dir in candidate_roots:
            if not base_dir:
                continue
            candidate = os.path.join(base_dir, APP_DATA_DIR_NAME)
            try:
                os.makedirs(candidate, exist_ok=True)
                probe = os.path.join(candidate, ".write-test")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.remove(probe)
                return candidate
            except OSError:
                continue
        return os.path.dirname(sys.executable)
    return os.getcwd()


def load_backend_env() -> None:
    load_dotenv(ENV_FILE)
    load_dotenv(os.path.join(runtime_dir(), ".env"), override=True)

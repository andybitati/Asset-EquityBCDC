import os
import sys

from dotenv import load_dotenv


BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_FILE = os.path.join(BACKEND_DIR, ".env")


def runtime_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()


def load_backend_env() -> None:
    load_dotenv(ENV_FILE)
    load_dotenv(os.path.join(runtime_dir(), ".env"), override=True)

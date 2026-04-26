import hashlib
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

HASH_REGISTRY_PATH = Path("data/raw/hash_registry.json")

def get_file_hash(file_path: Path) -> str:
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def load_registry() -> dict:
    if HASH_REGISTRY_PATH.exists():
        try:
            return json.loads(HASH_REGISTRY_PATH.read_text(encoding='utf-8'))
        except:
            return {}
    return {}

def save_registry(registry: dict):
    HASH_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HASH_REGISTRY_PATH.write_text(json.dumps(registry, indent=2), encoding='utf-8')

def is_duplicate_hash(file_hash: str) -> bool:
    registry = load_registry()
    return file_hash in registry

def register_file(file_hash: str, file_path_str: str):
    registry = load_registry()
    registry[file_hash] = file_path_str
    save_registry(registry)

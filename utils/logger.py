import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Silence noisy third-party loggers
for _name in ("httpx", "sentence_transformers", "filelock", "tensorflow", "fsspec"):
    logging.getLogger(_name).setLevel(logging.WARNING)

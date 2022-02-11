import logging
from pathlib import Path
from time import strftime

log_path: Path = Path("/aux1/trace-tool/logs")
log_file = log_path / f"trace-tool_{strftime('%Y%m%d')}.log"

if not log_path.is_dir():
    log_path.mkdir(parents=True, exist_ok=True)

logging.basicConfig(filename=log_file, filemode='a', format='%(asctime)s [%(levelname)s] %(message)s',
                    level=logging.DEBUG)

logger = logging.getLogger()


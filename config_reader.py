import json
from typing import Dict
from pathlib import Path
from trace_logger import logger

CONFIG = "trace_tool_conf.json"
logging = logger

try:
    with open(CONFIG, "r") as json_conf:
        config: Dict = json.load(json_conf)
except FileNotFoundError:
    logging.error("Config file not found")
except json.JSONDecodeError:
    logging.error("Json format of the config is not correct.")


# def get_log_path():
#     try:
#         path: str = config["TRACE-TOOL"]["log_path"]
#         if not path:
#             raise ValueError("path_log not configured.")
#         log_path = Path(path)
#     except KeyError as e:
#         raise KeyError(f"No key {e} in config.")
#     return log_path


def get_app_log(app: str) -> Path:
    try:
        log_path: str = config[app]["path"]
        if not log_path:
            logging.error(f"log_path for {app} is not configured.")
        prefix: str = config[app]["prefix"]
        if not prefix:
            logging.error(f"log prefix for {app} is not configured.")
        suffix: str = config[app]["suffix"]
        if not suffix:
            logging.error(f"log suffix for {app} is not configured.")
        app_log: Path = Path(log_path, f"{prefix}(datetime){suffix}")
    except KeyError as e:
        logging.error(f"No {e} in config.")
    return app_log


def get_results_dir() -> Path:
    try:
        results_path: Path = config["TRACE-TOOL"].get("results_path", "/aux1/trace-tool/results")
    except KeyError as e:
        logging.error(f"No {e} in config.")
    return results_path

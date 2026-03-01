import logging
import logging.handlers
from pathlib import Path
from typing import Optional


def setup_global_logger(
    log_level: int = logging.INFO,
    log_filename: str = "app.log",
    log_dir: str = "logs",
    console_output: bool = True,
    detailed_format: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    root_logger.handlers.clear()
    
    if detailed_format:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    else:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    file_path = log_path / log_filename
    
    file_handler = logging.handlers.RotatingFileHandler(
        file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
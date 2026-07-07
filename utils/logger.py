import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(name: str = "resume_screener", log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
    """Sets up a rotating file logger and console logger."""
    logger = logging.getLogger(name)
    
    # If logger is already configured, return it to avoid duplicate handlers
    if logger.handlers:
        return logger
        
    logger.setLevel(level)
    
    # Formatter for logs
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Ensure logs directory exists if a path is provided
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        
    # Rotating File Handler (10MB size limit, backup count of 3)
    try:
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=3, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Failed to set up file logger handler: {e}. Logging to console only.")
        
    return logger

# Get a default logger instance
logger = setup_logger()

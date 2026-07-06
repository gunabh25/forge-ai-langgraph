"""Structured logging configuration for ForgeAI."""

import logging
import sys
import json
from typing import Any, Dict

# Standard LogRecord attributes to exclude from extra metadata
STANDARD_RECORD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime"
}

class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured logs with metadata key-value pairs."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Calculate standard message first
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
            
        asctime = getattr(record, "asctime", None) or self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z")
        log_data = {
            "timestamp": asctime,
            "level": record.levelname,
            "logger": record.name,
            "message": record.message
        }
        
        # Capture all extra fields passed via extra={...}
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in STANDARD_RECORD_ATTRS:
                extra_fields[key] = value
                
        if extra_fields:
            log_data["metadata"] = extra_fields
            
        # Format as string with key-values for cleaner CLI reading
        metadata_str = f" | metadata={json.dumps(extra_fields)}" if extra_fields else ""
        return f"{log_data['timestamp']} - {log_data['level']} - {log_data['logger']} - {log_data['message']}{metadata_str}"

def get_logger(name: str) -> logging.Logger:
    """Get or create a configured structured logger.
    
    Args:
        name: Logger name.
        
    Returns:
        logging.Logger instance.
    """
    logger = logging.getLogger(name)
    
    # If logger already has handlers, don't duplicate them
    if logger.handlers:
        return logger
        
    # Default to DEBUG, handler controls display level
    logger.setLevel(logging.DEBUG)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    formatter = StructuredFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z")
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    return logger

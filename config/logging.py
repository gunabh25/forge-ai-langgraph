"""Structured logging configuration for ForgeAI."""

import logging
import sys
import json
import os
from logging.handlers import RotatingFileHandler
from typing import Any, Dict
from rich.logging import RichHandler
from core.context import get_telemetry_context

# Ensure logs directory exists
LOGS_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

STANDARD_RECORD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime", "event_type"
}

class JSONLinesFormatter(logging.Formatter):
    """Outputs structured JSON lines combining contextvars and extra log fields."""
    
    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
            
        asctime = getattr(record, "asctime", None) or self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z")
        
        # Base event object
        log_data = {
            "timestamp": asctime,
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "event_type": getattr(record, "event_type", "LogEvent")
        }
        
        # Inject standard telemetry from contextvars
        context_data = get_telemetry_context()
        log_data.update(context_data)
        
        # Add any extra fields passed via extra={...}
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in STANDARD_RECORD_ATTRS and key not in log_data:
                extra_fields[key] = value
                
        if extra_fields:
            log_data["metadata"] = extra_fields
            
        return json.dumps(log_data, default=str)

class StandardTextFormatter(logging.Formatter):
    """Standard text formatting for forgeai.log"""
    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        asctime = getattr(record, "asctime", None) or self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z")
        
        context_data = get_telemetry_context()
        ctx_str = " ".join([f"[{k}={v}]" for k, v in context_data.items() if v])
        
        extra_fields = {k: v for k, v in record.__dict__.items() if k not in STANDARD_RECORD_ATTRS and k not in context_data and k != "event_type"}
        meta_str = f" | metadata={json.dumps(extra_fields, default=str)}" if extra_fields else ""
        
        return f"{asctime} - {record.levelname} - {record.name} - {ctx_str} - {record.message}{meta_str}"

def get_logger(name: str) -> logging.Logger:
    """Get or create a configured structured logger."""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.DEBUG)
    
    # 1. Rich CLI Handler
    rich_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_path=False,
        show_time=False,
        omit_repeated_times=False
    )
    rich_handler.setLevel(logging.INFO)
    logger.addHandler(rich_handler)
    
    # 2. JSON Lines File Handler
    jsonl_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, "forgeai.jsonl"),
        maxBytes=10 * 1024 * 1024, # 10 MB
        backupCount=5,
        encoding="utf-8"
    )
    jsonl_handler.setLevel(logging.DEBUG)
    jsonl_formatter = JSONLinesFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z")
    jsonl_handler.setFormatter(jsonl_formatter)
    logger.addHandler(jsonl_handler)
    
    # 3. Standard Text File Handler
    text_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, "forgeai.log"),
        maxBytes=10 * 1024 * 1024, # 10 MB
        backupCount=5,
        encoding="utf-8"
    )
    text_handler.setLevel(logging.DEBUG)
    text_formatter = StandardTextFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z")
    text_handler.setFormatter(text_formatter)
    logger.addHandler(text_handler)
    
    logger.propagate = False
    return logger

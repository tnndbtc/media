"""Structured logging configuration using structlog."""

import json
import logging
import sys
from functools import lru_cache

import structlog


class PrettyJsonRenderer:
    """Custom renderer for human-readable logs with pretty-printed JSON.

    Outputs logs in format:
        LEVEL TIMESTAMP logger event - {
          "key": "value",
          ...
        }
    """

    def __call__(
        self,
        logger: structlog.types.WrappedLogger,
        method_name: str,
        event_dict: structlog.types.EventDict,
    ) -> str:
        """Render the log event as a human-readable string with pretty JSON."""
        timestamp = event_dict.pop("timestamp", "")
        level = event_dict.pop("level", method_name).upper()
        event = event_dict.pop("event", "")

        # Build prefix: LEVEL TIMESTAMP logger event -
        prefix = f"{level} {timestamp} {logger} {event} -"

        if event_dict:
            # Pretty-print the remaining data as JSON
            json_str = json.dumps(event_dict, indent=2, ensure_ascii=False, default=str)
            lines = json_str.split("\n")
            # First line on same line as prefix, rest indented with prefix
            if len(lines) > 1:
                formatted_lines = [f"{prefix} {lines[0]}"]
                for line in lines[1:]:
                    formatted_lines.append(f"{prefix}   {line}")
                return "\n".join(formatted_lines)
            return f"{prefix} {json_str}"
        return prefix


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format - "json" (compact), "pretty" (human-readable), "console" (colored dev)
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Suppress verbose HTTP transport logs (httpx, httpcore, openai internal)
    # These should only show at DEBUG level
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("openai._base_client").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)

    # Common processors
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # Select renderer based on log format
    if log_format == "json":
        # Compact JSON format for production
        final_processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ]
    elif log_format == "pretty":
        # Human-readable format with pretty-printed JSON
        final_processors = shared_processors + [
            structlog.processors.format_exc_info,
            PrettyJsonRenderer(),
        ]
    else:
        # Console format for development (colored)
        final_processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=final_processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


@lru_cache
def get_logger(name: str = "app") -> structlog.stdlib.BoundLogger:
    """Get a logger instance.

    Args:
        name: Logger name (typically module name)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)

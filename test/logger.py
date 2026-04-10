"""
logger.py — A beautiful, feature-rich Python logger.

Usage:
    from logger import get_logger

    log = get_logger("my_app")
    log.debug("Initialising systems...")
    log.info("Server started on port 8080")
    log.success("Connected to database")
    log.warning("Cache miss rate is high")
    log.error("Failed to reach upstream service")
    log.critical("Out of memory — shutting down")

    # With context (structured key=value pairs)
    log.info("Request received", method="GET", path="/api/users", status=200)

    # Timing a block
    with log.timer("heavy computation"):
        ...  # your code here

    # Section dividers
    log.section("STARTUP SEQUENCE")
"""

import logging
import sys
import time
import contextlib
from datetime import datetime
from typing import Any


# ── ANSI colour palette ────────────────────────────────────────────────────────

RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

# Foreground colours
FG_GREY    = "\033[38;5;245m"
FG_CYAN    = "\033[38;5;117m"
FG_GREEN   = "\033[38;5;120m"
FG_YELLOW  = "\033[38;5;221m"
FG_ORANGE  = "\033[38;5;209m"
FG_RED     = "\033[38;5;203m"
FG_MAGENTA = "\033[38;5;213m"
FG_WHITE   = "\033[38;5;255m"
FG_BLUE    = "\033[38;5;75m"

# Accent backgrounds (for level badge)
BG_GREY    = "\033[48;5;237m"
BG_CYAN    = "\033[48;5;31m"
BG_GREEN   = "\033[48;5;28m"
BG_YELLOW  = "\033[48;5;136m"
BG_ORANGE  = "\033[48;5;130m"
BG_RED     = "\033[48;5;124m"
BG_MAGENTA = "\033[48;5;90m"


# ── Custom SUCCESS level (between INFO and WARNING) ────────────────────────────

SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")


# ── Level config: (badge_bg, badge_fg, message_colour, icon) ──────────────────

LEVEL_STYLES: dict[int, tuple[str, str, str, str]] = {
    logging.DEBUG:   (BG_GREY,    FG_WHITE,  FG_GREY,    "·"),
    logging.INFO:    (BG_CYAN,    FG_WHITE,  FG_WHITE,   "ℹ"),
    SUCCESS_LEVEL:   (BG_GREEN,   FG_WHITE,  FG_GREEN,   "✔"),
    logging.WARNING: (BG_YELLOW,  FG_WHITE,  FG_YELLOW,  "⚠"),
    logging.ERROR:   (BG_RED,     FG_WHITE,  FG_ORANGE,  "✖"),
    logging.CRITICAL:(BG_MAGENTA, FG_WHITE,  FG_MAGENTA, "☠"),
}

LEVEL_LABELS: dict[int, str] = {
    logging.DEBUG:    "DEBUG   ",
    logging.INFO:     "INFO    ",
    SUCCESS_LEVEL:    "SUCCESS ",
    logging.WARNING:  "WARNING ",
    logging.ERROR:    "ERROR   ",
    logging.CRITICAL: "CRITICAL",
}


def _supports_colour(stream=None) -> bool:
    """Return True when the stream can render ANSI escape codes."""
    stream = stream or sys.stderr
    return hasattr(stream, "isatty") and stream.isatty()


# ── Custom formatter ───────────────────────────────────────────────────────────

class PrettyFormatter(logging.Formatter):
    """
    Renders log records like:

    12:34:56.789  ╷ ℹ INFO     ╷ my_app  ╷  Message text   key=value …
    """

    SEP = f"{FG_GREY}│{RESET}"

    def __init__(self, use_colour: bool = True, show_name: bool = True):
        super().__init__()
        self.use_colour = use_colour
        self.show_name  = show_name

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        # ── timestamp ──────────────────────────────────────────────────────
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S") \
             + f".{int(record.msecs):03d}"

        if self.use_colour:
            ts_str = f"{DIM}{FG_GREY}{ts}{RESET}"
        else:
            ts_str = ts

        # ── level badge ────────────────────────────────────────────────────
        lvl = record.levelno
        label = LEVEL_LABELS.get(lvl, f"{record.levelname:<8}")

        if self.use_colour:
            bg, fg, msg_colour, icon = LEVEL_STYLES.get(
                lvl, (BG_GREY, FG_WHITE, FG_WHITE, "·")
            )
            level_str = f"{bg}{fg}{BOLD} {icon} {label}{RESET}"
        else:
            level_str = label.strip()
            msg_colour = ""

        # ── logger name ────────────────────────────────────────────────────
        name_str = ""
        if self.show_name:
            name = record.name[:16]
            if self.use_colour:
                name_str = f" {FG_BLUE}{BOLD}{name:<16}{RESET} {self.SEP}"
            else:
                name_str = f" {name:<16} │"

        # ── message ────────────────────────────────────────────────────────
        msg = record.getMessage()
        if self.use_colour:
            msg_str = f" {msg_colour}{msg}{RESET}"
        else:
            msg_str = f" {msg}"

        # ── structured extras (key=value pairs stored in record.extras) ───
        extras = getattr(record, "_extras", {})
        extra_str = ""
        if extras:
            parts = []
            for k, v in extras.items():
                if self.use_colour:
                    parts.append(f"{DIM}{FG_GREY}{k}{RESET}={FG_CYAN}{v}{RESET}")
                else:
                    parts.append(f"{k}={v}")
            extra_str = "  " + "  ".join(parts)

        # ── exception ──────────────────────────────────────────────────────
        exc_str = ""
        if record.exc_info:
            exc_str = "\n" + self.formatException(record.exc_info)

        sep = self.SEP if self.use_colour else "│"

        return (
            f"{ts_str}  {sep} {level_str} {sep}{name_str}"
            f"{msg_str}{extra_str}{exc_str}"
        )


# ── Pretty handler ─────────────────────────────────────────────────────────────

class PrettyHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:  # noqa: BLE001
            self.handleError(record)


# ── Logger wrapper ─────────────────────────────────────────────────────────────

class Logger:
    """Thin wrapper around :class:`logging.Logger` with extra conveniences."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    # ── low-level helpers ──────────────────────────────────────────────────

    def _log(self, level: int, msg: str, **kwargs: Any) -> None:
        if self._logger.isEnabledFor(level):
            record = self._logger.makeRecord(
                self._logger.name, level, "(unknown)", 0, msg, (), None
            )
            record._extras = kwargs  # type: ignore[attr-defined]
            self._logger.handle(record)

    # ── public API ─────────────────────────────────────────────────────────

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.INFO, msg, **kwargs)

    def success(self, msg: str, **kwargs: Any) -> None:
        self._log(SUCCESS_LEVEL, msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, msg, **kwargs)

    def critical(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, msg, **kwargs)

    def exception(self, msg: str, **kwargs: Any) -> None:
        """Log an ERROR and attach the current exception traceback."""
        if self._logger.isEnabledFor(logging.ERROR):
            record = self._logger.makeRecord(
                self._logger.name, logging.ERROR, "(unknown)", 0,
                msg, (), sys.exc_info()
            )
            record._extras = kwargs  # type: ignore[attr-defined]
            self._logger.handle(record)

    # ── section divider ────────────────────────────────────────────────────

    def section(self, title: str = "") -> None:
        """Print a visual section divider (not routed through logging levels)."""
        width = 72
        if title:
            pad   = max(0, width - len(title) - 4)
            left  = pad // 2
            right = pad - left
            line  = f"{'─' * left}  {title}  {'─' * right}"
        else:
            line = "─" * width

        handler = self._get_stream_handler()
        use_colour = _supports_colour(getattr(handler, "stream", sys.stdout))

        if use_colour:
            print(f"\n{DIM}{FG_GREY}{line}{RESET}\n", file=sys.stdout)
        else:
            print(f"\n{line}\n", file=sys.stdout)

    # ── timer context manager ──────────────────────────────────────────────

    @contextlib.contextmanager
    def timer(self, label: str = "operation"):
        """Context manager that logs how long a block of code took."""
        self.info(f"Starting {label}…")
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - t0
            self.success(f"Finished {label}", elapsed=f"{elapsed:.3f}s")

    # ── internals ──────────────────────────────────────────────────────────

    def _get_stream_handler(self):
        for h in self._logger.handlers:
            if isinstance(h, logging.StreamHandler):
                return h
        return None

    def set_level(self, level: int | str) -> None:
        self._logger.setLevel(level)

    @property
    def name(self) -> str:
        return self._logger.name


# ── Factory ────────────────────────────────────────────────────────────────────

_loggers: dict[str, Logger] = {}


def get_logger(
    name: str = "app",
    level: int = logging.DEBUG,
    *,
    colour: bool | None = None,
    show_name: bool = True,
    stream=None,
) -> Logger:
    """
    Return (or create) a named :class:`Logger`.

    Parameters
    ----------
    name       : Logger name shown in every line.
    level      : Minimum level to emit (default: DEBUG).
    colour     : Force colour on/off. ``None`` = auto-detect.
    show_name  : Whether to print the logger name column.
    stream     : Output stream (default: ``sys.stdout``).
    """
    if name in _loggers:
        return _loggers[name]

    stream = stream or sys.stdout
    use_colour = colour if colour is not None else _supports_colour(stream)

    raw = logging.getLogger(name)
    raw.setLevel(level)
    raw.propagate = False

    if not raw.handlers:
        handler = PrettyHandler(stream)
        handler.setFormatter(PrettyFormatter(use_colour=use_colour, show_name=show_name))
        raw.addHandler(handler)

    wrapped = Logger(raw)
    _loggers[name] = wrapped
    return wrapped


# ── Demo ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log = get_logger("demo")

    log.section("BOOT SEQUENCE")
    log.debug("Reading configuration file", path="/etc/app/config.toml")
    log.info("Server initialising", host="0.0.0.0", port=8080)
    log.success("Database connection established", pool_size=10)
    log.warning("Disk usage above threshold", used="87%", mount="/var")
    log.error("Upstream timeout", service="payments-api", retries=3)
    log.critical("Out of memory — initiating graceful shutdown")

    log.section("TIMED BLOCK")
    with log.timer("fibonacci(30)"):
        def fib(n):
            return n if n < 2 else fib(n - 1) + fib(n - 2)
        result = fib(30)
    log.info("Computed result", value=result)

    log.section()
    log.info("All done.")

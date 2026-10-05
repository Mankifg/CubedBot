import atexit
import io
import os
import queue
import sys
import threading
import time
import uuid
from datetime import datetime, timezone


LOG_TABLE = "bot_logs"
DEFAULT_BATCH_SIZE = 100
DEFAULT_FLUSH_SECONDS = 2
DEFAULT_QUEUE_SIZE = 5000
PRUNE_INTERVAL_SECONDS = 6 * 60 * 60


def database_logging_enabled():
    return os.getenv("DATABASE_LOGGING_ENABLED", "1").strip().lower() in {
        "1", "true", "yes", "on",
    }


def infer_level(message, stream):
    upper = message.lstrip().upper()
    if upper.startswith("[ERROR]") or stream == "stderr":
        return "ERROR"
    if upper.startswith("[WARN]") or upper.startswith("[WARNING]"):
        return "WARN"
    if upper.startswith("[DEBUG]"):
        return "DEBUG"
    return "INFO"


class DatabaseLogSink:
    def __init__(
        self,
        client,
        original_stderr,
        batch_size=DEFAULT_BATCH_SIZE,
        flush_seconds=DEFAULT_FLUSH_SECONDS,
        queue_size=DEFAULT_QUEUE_SIZE,
    ):
        self.client = client
        self.original_stderr = original_stderr
        self.batch_size = batch_size
        self.flush_seconds = flush_seconds
        self.queue = queue.Queue(maxsize=queue_size)
        self.stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self._run,
            name="database-log-writer",
            daemon=True,
        )
        self._last_failure_notice = -3600
        self._last_prune = -PRUNE_INTERVAL_SECONDS

    def start(self):
        self.thread.start()

    def enqueue(self, message, stream):
        message = str(message).rstrip("\r\n")
        if not message:
            return
        row = {
            "entry_id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": infer_level(message, stream),
            "stream": stream,
            "message": message[:8000],
        }
        try:
            self.queue.put_nowait(row)
        except queue.Full:
            self._notice("database log queue is full; dropping log lines")

    def _notice(self, message):
        now = time.monotonic()
        if now - self._last_failure_notice < 3600:
            return
        self._last_failure_notice = now
        try:
            self.original_stderr.write(f"[WARN] {message}\n")
            self.original_stderr.flush()
        except Exception:
            pass

    def _insert(self, rows):
        (
            self.client.table(LOG_TABLE)
            .upsert(
                rows,
                on_conflict="entry_id",
                ignore_duplicates=True,
                returning="minimal",
            )
            .execute()
        )

    def _prune(self):
        self.client.rpc("prune_bot_logs").execute()
        self._last_prune = time.monotonic()

    def _run(self):
        pending = []
        retry_delay = 1
        while not self.stop_event.is_set() or pending or not self.queue.empty():
            if not pending:
                try:
                    pending.append(self.queue.get(timeout=self.flush_seconds))
                except queue.Empty:
                    pass
                while len(pending) < self.batch_size:
                    try:
                        pending.append(self.queue.get_nowait())
                    except queue.Empty:
                        break

            try:
                if pending:
                    self._insert(pending)
                    pending.clear()
                    retry_delay = 1
                if time.monotonic() - self._last_prune >= PRUNE_INTERVAL_SECONDS:
                    self._prune()
            except Exception as exc:
                self._notice(
                    "database logging unavailable: "
                    f"{type(exc).__name__}: {exc}"
                )
                self.stop_event.wait(retry_delay)
                retry_delay = min(retry_delay * 2, 60)

    def close(self, timeout=5):
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=timeout)


class TeeLogStream(io.TextIOBase):
    def __init__(self, original, sink, stream_name):
        self.original = original
        self.sink = sink
        self.stream_name = stream_name
        self.buffer = ""
        self.lock = threading.Lock()

    @property
    def encoding(self):
        return getattr(self.original, "encoding", "utf-8")

    def write(self, text):
        text = str(text)
        written = self.original.write(text)
        with self.lock:
            self.buffer += text
            while "\n" in self.buffer:
                line, self.buffer = self.buffer.split("\n", 1)
                self.sink.enqueue(line, self.stream_name)
        return written if written is not None else len(text)

    def flush(self):
        self.original.flush()

    def isatty(self):
        return bool(getattr(self.original, "isatty", lambda: False)())


_installed_sink = None


def install_database_logging(client_factory, enabled=None):
    global _installed_sink
    if _installed_sink is not None:
        return _installed_sink
    if enabled is None:
        enabled = database_logging_enabled()
    if not enabled:
        return None

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    client = client_factory()
    sink = DatabaseLogSink(client, original_stderr)
    sys.stdout = TeeLogStream(original_stdout, sink, "stdout")
    sys.stderr = TeeLogStream(original_stderr, sink, "stderr")
    sink.start()
    atexit.register(sink.close)
    _installed_sink = sink
    return sink

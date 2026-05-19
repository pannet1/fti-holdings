import logging
import logging.handlers
import queue
import atexit
import sys
from typing import Any


class AsyncLogger:
    """
    Manages the setup, starting, and stopping of the asynchronous logging system
    for the entire application. It configures the root logger to use a QueueHandler.
    """

    def __init__(self, level=logging.INFO, log_file: Any = None):
        """
        Initializes the manager but does not start the background thread yet.
        :param level: The minimum log level to capture (e.g., logging.INFO).
        :param log_file: If provided, all logs go to this file. If None, logs
                         only go to stdout.
        """
        self._level = level
        self._log_file_path = log_file
        self._listener = None
        self._log_queue = queue.Queue(-1)

        # Configure the log format
        self._formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - **%(name)s** - %(threadName)s - %(message)s"
        )

    def start(self):
        """Starts the asynchronous logging listener thread."""
        if self._listener is not None:
            print("Async logging system is already running.")
            return

        # 1. Define the 'Slow' Handlers (I/O writers)
        slow_handlers = []

        if self._log_file_path:
            # Request: Log to file if path is provided
            file_handler = logging.handlers.RotatingFileHandler(
                self._log_file_path, maxBytes=10 * 1024 * 1024, backupCount=5
            )
            file_handler.setFormatter(self._formatter)
            slow_handlers.append(file_handler)
            print(f"Async logging enabled, outputting to: {self._log_file_path}")
        else:
            # Request: Log to stdout if no file path is provided
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(self._formatter)
            slow_handlers.append(console_handler)
            print("Async logging enabled, outputting only to console.")

        # 2. Create and Start the QueueListener (The Consumer Thread)
        self._listener = logging.handlers.QueueListener(self._log_queue, *slow_handlers)
        self._listener.start()
        atexit.register(self.stop)  # Auto-flush logs on process exit

        # 3. Configure the Root Logger (The Producer)
        root_logger = logging.getLogger()
        root_logger.setLevel(self._level)

        # Clear existing handlers to ensure clean configuration
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # 4. Attach the QueueHandler (The fast, non-blocking handler)
        queue_handler = logging.handlers.QueueHandler(self._log_queue)
        root_logger.addHandler(queue_handler)

    def stop(self):
        """Stops the background logging thread and flushes any pending logs."""
        if self._listener:
            self._listener.stop()
            self._listener = None
            print("\nAsync logger stopped and all logs flushed.")

    def get_logger_function(self):
        """
        Returns the standard logging.getLogger function for modules to use.
        This allows modules to call getLogger(__name__) to set their name.
        """
        return logging.getLogger


# -----------------------------------------------------------------------------

"""
Enhanced Parallelization Manager for neurpi.

This module provides a centralized, robust system for managing parallel processes
with improved error handling, health monitoring, and resource management.
"""

from __future__ import annotations

import contextlib
import logging
import multiprocessing as mp
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from queue import Empty
from typing import Any

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False


class ProcessState(Enum):
    """Process state enumeration."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    CRASHED = "crashed"


@dataclass
class ProcessConfig:
    """Configuration for a managed process."""

    name: str
    target_func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    daemon: bool = True
    auto_restart: bool = False
    max_restarts: int = 3
    restart_delay: float = 1.0
    timeout: float = 30.0
    priority: int = 0  # Higher values = higher priority
    in_queue: Any | None = None  # mp.Queue type hint causes issues
    out_queue: Any | None = None
    error_queue: Any | None = None
    stop_event: Any | None = None


@dataclass
class ProcessInfo:
    """Information about a managed process."""

    config: ProcessConfig
    process: Any | None = None  # mp.Process type hint causes issues
    state: ProcessState = ProcessState.IDLE
    start_time: float | None = None
    restart_count: int = 0
    last_heartbeat: float | None = None
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    error_message: str | None = None


@dataclass
class ProcessWrapperConfig:
    """Configuration for process wrapper to reduce argument count."""

    target_func: Callable
    args: tuple
    kwargs: dict[str, Any]
    in_queue: Any
    out_queue: Any
    error_queue: Any
    stop_event: Any


class ProcessMonitor(threading.Thread):
    """Thread for monitoring process health and performance."""

    def __init__(self, manager, check_interval: float = 1.0):
        super().__init__(daemon=True)
        self.manager = manager
        self.check_interval = check_interval
        self.stop_event = threading.Event()
        self.logger = logging.getLogger(f"{__name__}.ProcessMonitor")

    def run(self):
        """Monitor process health and performance."""
        while not self.stop_event.is_set():
            self._check_processes()
            time.sleep(self.check_interval)

    def _check_processes(self):
        """Check all managed processes."""
        current_time = time.time()

        processes_copy = list(self.manager.processes.items())
        for process_id, info in processes_copy:
            self._check_single_process(process_id, info, current_time)

    def _check_single_process(self, process_id: str, info: ProcessInfo, current_time: float):
        """Check a single process for health and performance."""
        try:
            if info.process and info.process.is_alive():
                self._update_performance_metrics(info)
                self._check_heartbeat_timeout(process_id, info, current_time)
            elif info.state == ProcessState.RUNNING:
                # Process died unexpectedly
                self.logger.warning(f"Process {process_id} died unexpectedly")
                self._handle_process_crash(process_id, info)
        except (OSError, AttributeError):
            self.logger.exception(f"Error checking process {process_id}")

    def _update_performance_metrics(self, info: ProcessInfo):
        """Update performance metrics for a process."""
        if not PSUTIL_AVAILABLE or not info.process:
            return

        with contextlib.suppress(Exception):
            if psutil is not None:
                proc = psutil.Process(info.process.pid)
                info.cpu_percent = proc.cpu_percent()
                info.memory_percent = proc.memory_percent()

    def _check_heartbeat_timeout(self, process_id: str, info: ProcessInfo, current_time: float):
        """Check for heartbeat timeout."""
        if info.last_heartbeat and current_time - info.last_heartbeat > info.config.timeout:
            self.logger.warning(f"Process {process_id} heartbeat timeout")
            self._handle_process_timeout(process_id, info)

    def _handle_process_timeout(self, process_id: str, info: ProcessInfo):
        """Handle process timeout."""
        info.state = ProcessState.ERROR
        info.error_message = "Process timeout"

        if info.config.auto_restart and info.restart_count < info.config.max_restarts:
            self.manager.restart_process_internal(process_id, info)
        else:
            self.manager.stop_process_internal(process_id, info)

    def _handle_process_crash(self, process_id: str, info: ProcessInfo):
        """Handle process crash."""
        info.state = ProcessState.CRASHED

        if info.config.auto_restart and info.restart_count < info.config.max_restarts:
            self.manager.restart_process_internal(process_id, info)
        else:
            info.state = ProcessState.STOPPED

    def stop(self):
        """Stop the monitor."""
        self.stop_event.set()


class CommunicationHub:
    """Centralized communication management."""

    def __init__(self):
        self.queues: dict[str, Any] = {}
        self.events: dict[str, Any] = {}
        self.locks: dict[str, Any] = {}
        self.logger = logging.getLogger(f"{__name__}.CommunicationHub")

    def create_queue(self, name: str, maxsize: int = 0):
        """Create and register a queue."""
        if name in self.queues:
            self.logger.warning(f"Queue {name} already exists")
            return self.queues[name]

        queue = mp.Queue(maxsize=maxsize)
        self.queues[name] = queue
        self.logger.debug(f"Created queue: {name}")
        return queue

    def create_event(self, name: str):
        """Create and register an event."""
        if name in self.events:
            self.logger.warning(f"Event {name} already exists")
            return self.events[name]

        event = mp.Event()
        self.events[name] = event
        self.logger.debug(f"Created event: {name}")
        return event

    def create_lock(self, name: str):
        """Create and register a lock."""
        if name in self.locks:
            self.logger.warning(f"Lock {name} already exists")
            return self.locks[name]

        lock = mp.Lock()
        self.locks[name] = lock
        self.logger.debug(f"Created lock: {name}")
        return lock

    def get_queue(self, name: str) -> Any | None:
        """Get a queue by name."""
        return self.queues.get(name)

    def get_event(self, name: str) -> Any | None:
        """Get an event by name."""
        return self.events.get(name)

    def get_lock(self, name: str) -> Any | None:
        """Get a lock by name."""
        return self.locks.get(name)

    def cleanup(self):
        """Cleanup all communication objects."""
        # Close queues
        for _name, queue in list(self.queues.items()):
            with contextlib.suppress(OSError, AttributeError):
                queue.close()
                queue.join_thread()

        self.queues.clear()
        self.events.clear()
        self.locks.clear()


class ParallelManager:
    """
    Enhanced parallel process manager with health monitoring.

    This manager provides centralized process management with health monitoring,
    error handling, and resource management capabilities.
    """

    def __init__(self, monitor_interval: float = 1.0):
        self.processes: dict[str, ProcessInfo] = {}
        self.communication = CommunicationHub()
        self.monitor = ProcessMonitor(self, monitor_interval)
        self.executor = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="ParallelManager",
        )
        self.logger = logging.getLogger(f"{__name__}.ParallelManager")
        self._running = True

        # Start monitoring
        self.monitor.start()

    def register_process(self, process_id: str, config: ProcessConfig) -> str:
        """Register a process configuration."""
        if process_id in self.processes:
            msg = f"Process {process_id} already registered"
            raise ValueError(msg)

        # Create communication objects if not provided
        if config.in_queue is None:
            config.in_queue = self.communication.create_queue(f"{process_id}_in")
        if config.out_queue is None:
            config.out_queue = self.communication.create_queue(f"{process_id}_out")
        if config.error_queue is None:
            config.error_queue = self.communication.create_queue(f"{process_id}_error")
        if config.stop_event is None:
            config.stop_event = self.communication.create_event(f"{process_id}_stop")

        info = ProcessInfo(config=config)
        self.processes[process_id] = info

        self.logger.info(f"Registered process: {process_id}")
        return process_id

    def start_process(self, process_id: str) -> bool:
        """Start a registered process."""
        if process_id not in self.processes:
            self.logger.error(f"Process {process_id} not registered")
            return False

        info = self.processes[process_id]

        if info.state == ProcessState.RUNNING:
            self.logger.warning(f"Process {process_id} already running")
            return True

        try:
            info.state = ProcessState.STARTING
            info.start_time = time.time()

            # Create process wrapper arguments
            wrapper_config = ProcessWrapperConfig(
                target_func=info.config.target_func,
                args=info.config.args,
                kwargs=info.config.kwargs,
                in_queue=info.config.in_queue,
                out_queue=info.config.out_queue,
                error_queue=info.config.error_queue,
                stop_event=info.config.stop_event,
            )

            info.process = mp.Process(
                target=self._process_wrapper,
                args=(wrapper_config,),
                daemon=info.config.daemon,
                name=f"NeuRPi_{process_id}",
            )

            info.process.start()
            info.state = ProcessState.RUNNING

            self.logger.info(f"Started process: {process_id} (PID: {info.process.pid})")
        except (OSError, ValueError):
            info.state = ProcessState.ERROR
            self.logger.exception(f"Failed to start process {process_id}")
            return False
        else:
            return True

    def stop_process(self, process_id: str, timeout: float = 10.0) -> bool:
        """Stop a running process."""
        if process_id not in self.processes:
            self.logger.error(f"Process {process_id} not found")
            return False

        info = self.processes[process_id]
        return self.stop_process_internal(process_id, info, timeout)

    def stop_process_internal(self, process_id: str, info: ProcessInfo, timeout: float = 10.0) -> bool:
        """Internal method to stop a process."""
        if not info.process or not info.process.is_alive():
            info.state = ProcessState.STOPPED
            return True

        try:
            info.state = ProcessState.STOPPING

            # Signal process to stop gracefully
            if info.config.stop_event:
                info.config.stop_event.set()

            # Wait for graceful shutdown
            info.process.join(timeout=timeout)

            if info.process.is_alive():
                # Force termination
                self.logger.warning(f"Force terminating process {process_id}")
                info.process.terminate()
                info.process.join(timeout=5.0)

                if info.process.is_alive():
                    # Kill if still alive
                    info.process.kill()
                    info.process.join()

            info.state = ProcessState.STOPPED
            self.logger.info(f"Stopped process: {process_id}")
        except (OSError, AttributeError):
            self.logger.exception(f"Error stopping process {process_id}")
            return False
        else:
            return True

    def restart_process(self, process_id: str) -> bool:
        """Restart a process."""
        if process_id not in self.processes:
            return False

        info = self.processes[process_id]
        return self.restart_process_internal(process_id, info)

    def restart_process_internal(self, process_id: str, info: ProcessInfo) -> bool:
        """Internal method to restart a process."""
        if info.restart_count >= info.config.max_restarts:
            self.logger.error(f"Process {process_id} exceeded max restarts")
            return False

        self.logger.info(f"Restarting process {process_id} (attempt {info.restart_count + 1})")

        # Stop current process
        self.stop_process_internal(process_id, info)

        # Wait restart delay
        time.sleep(info.config.restart_delay)

        # Clear stop event
        if info.config.stop_event:
            info.config.stop_event.clear()

        # Increment restart count
        info.restart_count += 1

        # Start process
        return self.start_process(process_id)

    def get_process_info(self, process_id: str) -> ProcessInfo | None:
        """Get process information."""
        return self.processes.get(process_id)

    def get_all_processes(self) -> dict[str, ProcessInfo]:
        """Get all process information."""
        return self.processes.copy()

    def send_message(self, process_id: str, message: Any, timeout: float = 1.0) -> bool:
        """Send message to a process."""
        if process_id not in self.processes:
            return False

        info = self.processes[process_id]
        if not info.config.in_queue:
            return False

        try:
            info.config.in_queue.put(message, timeout=timeout)
        except (OSError, ValueError):
            self.logger.exception(f"Failed to send message to {process_id}")
            return False
        else:
            return True

    def receive_message(self, process_id: str, timeout: float = 1.0) -> tuple[bool, Any]:
        """Receive message from a process."""
        if process_id not in self.processes:
            return False, None

        info = self.processes[process_id]
        if not info.config.out_queue:
            return False, None

        try:
            message = info.config.out_queue.get(timeout=timeout)
        except Empty:
            return False, None
        except (OSError, ValueError):
            self.logger.exception(f"Failed to receive message from {process_id}")
            return False, None
        else:
            return True, message

    def wait_for_message(self, process_id: str, message_type: str | None = None, timeout: float = 30.0) -> tuple[bool, Any]:
        """Wait for a specific type of message from a process."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            success, message = self.receive_message(process_id, timeout=0.1)
            if success and (message_type is None or (isinstance(message, dict) and message.get("type") == message_type)):
                return True, message
            time.sleep(0.01)

        return False, None

    def stop_all_processes(self, timeout: float = 10.0):
        """Stop all managed processes."""
        self.logger.info("Stopping all processes")

        # Get processes sorted by priority (higher priority stopped first)
        processes = sorted(
            self.processes.items(),
            key=lambda x: x[1].config.priority,
            reverse=True,
        )

        for process_id, info in processes:
            if info.state == ProcessState.RUNNING:
                self.stop_process(process_id, timeout)

    def cleanup(self):
        """Cleanup all resources."""
        if not self._running:
            return

        self._running = False

        # Stop all processes
        self.stop_all_processes()

        # Stop monitor
        self.monitor.stop()
        self.monitor.join(timeout=5.0)

        # Cleanup communication
        self.communication.cleanup()

        # Shutdown executor
        self.executor.shutdown(wait=True)

        self.logger.info("ParallelManager cleanup complete")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    @staticmethod
    def _process_wrapper(config: ProcessWrapperConfig):
        """Wrapper for managed processes with enhanced error handling."""
        process_id = mp.current_process().name
        logger = logging.getLogger(f"{__name__}.Process.{process_id}")

        try:
            # Send startup confirmation
            if config.out_queue:
                with contextlib.suppress(Exception):
                    config.out_queue.put(
                        {
                            "type": "startup",
                            "status": "started",
                            "pid": mp.current_process().pid,
                        }
                    )

            # Call target function with enhanced arguments
            enhanced_kwargs = config.kwargs.copy()
            enhanced_kwargs.update(
                {
                    "in_queue": config.in_queue,
                    "out_queue": config.out_queue,
                    "error_queue": config.error_queue,
                    "stop_event": config.stop_event,
                    "logger": logger,
                }
            )

            config.target_func(*config.args, **enhanced_kwargs)

        except Exception as e:
            error_msg = f"Process {process_id} error: {e}"
            logger.exception("Process error occurred")

            if config.error_queue:
                with contextlib.suppress(Exception):
                    config.error_queue.put(
                        {
                            "type": "error",
                            "message": error_msg,
                            "exception": str(e),
                        }
                    )

        finally:
            # Send shutdown confirmation
            if config.out_queue:
                with contextlib.suppress(Exception):
                    config.out_queue.put({"type": "shutdown", "status": "stopped"})

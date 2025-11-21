"""Dashboard startup orchestrator for foreground mode."""

import logging
import os
import platform
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

try:
    import requests  # type: ignore[import-untyped]
except ImportError:
    requests = None  # type: ignore[assignment]

from ..config.schema import BaselinrConfig
from .config_builder import build_connection_string

logger = logging.getLogger(__name__)


def wait_for_backend(port: int, host: str = "127.0.0.1", timeout: int = 30) -> bool:
    """
    Wait for the backend API to become responsive.

    Args:
        port: Backend port.
        host: Backend host.
        timeout: Maximum time to wait in seconds.

    Returns:
        True if backend is responsive, False otherwise.
    """
    if requests is None:
        logger.warning(
            "Requests library not found. Cannot perform backend health check. "
            "Please install it with 'pip install requests' for robust UI startup."
        )
        # Give backend a moment to start without health check
        time.sleep(2)
        return True

    url = f"http://{host}:{port}/"
    logger.info(f"Waiting for backend to be ready at {url} (timeout: {timeout}s)...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=1)
            if response.status_code == 200:
                logger.info("Backend is healthy.")
                return True
        except requests.exceptions.ConnectionError:
            pass  # Backend not yet up
        except Exception as e:
            logger.warning(f"Backend health check failed with unexpected error: {e}")
        time.sleep(0.5)
    logger.warning(
        f"Backend did not become healthy within {timeout} seconds, but continuing anyway."
    )
    return False


def start_dashboard_foreground(
    config: BaselinrConfig,
    backend_port: int = 8000,
    frontend_port: int = 3000,
    backend_host: str = "0.0.0.0",
) -> None:
    """
    Start both backend and frontend processes for the dashboard in foreground mode.

    This function blocks until Ctrl+C is pressed or one of the processes exits.
    Both processes run in the foreground, attached to the current terminal.

    Args:
        config: Baselinr configuration.
        backend_port: Port for the backend API.
        frontend_port: Port for the frontend UI.
        backend_host: Host for the backend API.

    Raises:
        FileNotFoundError: If dashboard directories are not found.
        RuntimeError: If processes fail to start.
    """
    dashboard_root = Path(__file__).parent.parent.parent / "dashboard"
    if not dashboard_root.is_dir():
        raise FileNotFoundError(f"Dashboard root directory not found at: {dashboard_root}")

    backend_path = dashboard_root / "backend"
    frontend_path = dashboard_root / "frontend"

    if not backend_path.is_dir():
        raise FileNotFoundError(f"Dashboard backend directory not found at: {backend_path}")
    if not frontend_path.is_dir():
        raise FileNotFoundError(f"Dashboard frontend directory not found at: {frontend_path}")

    # Build connection string from Baselinr config
    db_url = build_connection_string(config)

    # Prepare environment for backend
    backend_env = os.environ.copy()
    backend_env["BASELINR_DB_URL"] = db_url
    backend_env["API_HOST"] = backend_host
    backend_env["API_PORT"] = str(backend_port)
    backend_env["PYTHONUNBUFFERED"] = "1"  # Ensure output is unbuffered

    # Prepare environment for frontend
    frontend_env = os.environ.copy()
    frontend_env["NEXT_PUBLIC_API_URL"] = f"http://localhost:{backend_port}"
    frontend_env["PORT"] = str(frontend_port)
    frontend_env["PYTHONUNBUFFERED"] = "1"  # Ensure output is unbuffered

    # Start backend process (foreground, not detached)
    backend_cmd = [sys.executable, "main.py"]
    logger.info(f"Starting backend with command: {' '.join(backend_cmd)} in {backend_path}")
    logger.info(
        f"Backend environment: BASELINR_DB_URL={db_url}, "
        f"API_HOST={backend_host}, API_PORT={backend_port}"
    )

    backend_process = subprocess.Popen(
        backend_cmd,
        cwd=backend_path,
        env=backend_env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    if not backend_process.pid:
        raise RuntimeError("Failed to start backend process.")

    logger.info(f"Backend started with PID: {backend_process.pid}")

    # Wait for backend to be ready
    if not wait_for_backend(
        backend_port, "127.0.0.1" if backend_host == "0.0.0.0" else backend_host
    ):
        backend_process.terminate()
        backend_process.wait(timeout=5)
        raise RuntimeError("Backend did not become healthy. Aborting dashboard startup.")

    # Start frontend process (foreground, not detached)
    # Find npm executable - use which/where to find it in PATH
    npm_cmd = shutil.which("npm")
    if not npm_cmd:
        backend_process.terminate()
        backend_process.wait(timeout=5)
        raise RuntimeError(
            "npm not found in PATH. Please install Node.js (v18+) and ensure it's in your PATH."
        )

    # Check if node_modules exists, if not install dependencies
    node_modules_path = frontend_path / "node_modules"
    package_json_path = frontend_path / "package.json"

    if not package_json_path.exists():
        backend_process.terminate()
        backend_process.wait(timeout=5)
        raise FileNotFoundError(
            f"package.json not found in {frontend_path}. "
            f"Please ensure the frontend directory is properly set up."
        )

    if not node_modules_path.exists():
        logger.info("node_modules not found. Installing frontend dependencies...")
        use_shell = platform.system() == "Windows"
        install_process = subprocess.run(
            ["npm", "install"],
            cwd=frontend_path,
            env=frontend_env,
            shell=use_shell,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        if install_process.returncode != 0:
            backend_process.terminate()
            backend_process.wait(timeout=5)
            raise RuntimeError(
                "Failed to install frontend dependencies. Please run 'npm install' manually."
            )

    # On Windows, use shell=True to ensure PATH is properly resolved
    use_shell = platform.system() == "Windows"
    frontend_cmd = ["npm", "run", "dev"]
    logger.info(f"Starting frontend with command: {' '.join(frontend_cmd)} in {frontend_path}")
    logger.info(
        f"Frontend environment: PORT={frontend_port}, "
        f"NEXT_PUBLIC_API_URL={frontend_env['NEXT_PUBLIC_API_URL']}"
    )

    frontend_process = subprocess.Popen(
        frontend_cmd,
        cwd=frontend_path,
        env=frontend_env,
        stdout=sys.stdout,
        stderr=sys.stderr,
        shell=use_shell,
    )

    if not frontend_process.pid:
        backend_process.terminate()
        backend_process.wait(timeout=5)
        raise RuntimeError("Failed to start frontend process.")

    logger.info(f"Frontend started with PID: {frontend_process.pid}")

    # Give frontend a moment to start, then check if it's still running
    # This helps catch immediate failures like port conflicts
    time.sleep(2)
    if frontend_process.poll() is not None:
        # Frontend exited quickly, likely an error
        backend_process.terminate()
        backend_process.wait(timeout=5)
        error_msg = (
            f"Frontend process exited immediately with code {frontend_process.returncode}. "
            f"This usually indicates a startup error.\n"
            f"Common causes:\n"
            f"  - Port {frontend_port} is already in use "
            f"(try --port-frontend to use a different port)\n"
            f"  - Missing dependencies (check the error output above)\n"
            f"  - Configuration error\n"
            f"\nTo use a different frontend port, run:\n"
            f"  baselinr ui --config <config> --port-frontend <port>"
        )
        raise RuntimeError(error_msg)

    # Print startup messages
    try:
        from rich.console import Console

        console = Console()
        console.print("\n[green]✓ Baselinr Dashboard started[/green]\n")
        console.print(f"  [cyan]Backend API:[/cyan]  http://{backend_host}:{backend_port}")
        console.print(f"  [cyan]Frontend UI:[/cyan] http://localhost:{frontend_port}")
        console.print("  [dim]Press Ctrl+C to stop[/dim]\n")
    except ImportError:
        print("\n✓ Baselinr Dashboard started\n")
        print(f"  Backend API:  http://{backend_host}:{backend_port}")
        print(f"  Frontend UI: http://localhost:{frontend_port}")
        print("  Press Ctrl+C to stop\n")

    # Set up signal handler for graceful shutdown
    def signal_handler(signum, frame):
        """Handle Ctrl+C gracefully."""
        logger.info("Received interrupt signal, shutting down dashboard...")
        try:
            from rich.console import Console

            console = Console()
            console.print("\n[yellow]Shutting down dashboard...[/yellow]")
        except ImportError:
            print("\nShutting down dashboard...")

        # Terminate both processes
        if backend_process.poll() is None:
            backend_process.terminate()
        if frontend_process.poll() is None:
            frontend_process.terminate()

        # Wait for processes to terminate
        try:
            backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_process.kill()
        try:
            frontend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            frontend_process.kill()

        try:
            from rich.console import Console

            console = Console()
            console.print("[green]✓ Dashboard stopped[/green]\n")
        except ImportError:
            print("✓ Dashboard stopped\n")

        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Monitor both processes and wait for either to exit
    def monitor_process(process, name):
        """Monitor a process and log when it exits."""
        process.wait()
        logger.info(f"{name} process exited with code {process.returncode}")

    backend_thread = threading.Thread(
        target=monitor_process, args=(backend_process, "Backend"), daemon=True
    )
    frontend_thread = threading.Thread(
        target=monitor_process, args=(frontend_process, "Frontend"), daemon=True
    )

    backend_thread.start()
    frontend_thread.start()

    # Wait for either process to exit
    try:
        while backend_process.poll() is None and frontend_process.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

    # If we get here, one of the processes exited
    if backend_process.poll() is not None:
        logger.warning(f"Backend process exited with code {backend_process.returncode}")
        if frontend_process.poll() is None:
            frontend_process.terminate()
            frontend_process.wait(timeout=5)
    elif frontend_process.poll() is not None:
        logger.warning(f"Frontend process exited with code {frontend_process.returncode}")
        if backend_process.poll() is None:
            backend_process.terminate()
            backend_process.wait(timeout=5)

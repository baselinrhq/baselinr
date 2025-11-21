"""Dependency checking utilities for UI command."""

import logging
import platform
import shutil
import socket
import subprocess
from typing import Optional, Tuple

from ..config.schema import BaselinrConfig
from ..connectors.factory import create_connector

logger = logging.getLogger(__name__)


class DependencyError(Exception):
    """Raised when a required dependency is missing."""

    pass


def check_nodejs() -> Tuple[bool, Optional[str]]:
    """
    Check if Node.js and npm are installed and meet version requirements.

    Returns:
        Tuple of (is_installed, version_string or error_message)
    """
    try:
        # Find node executable - use which/where to find it in PATH
        node_cmd = shutil.which("node")
        if not node_cmd:
            return (
                False,
                (
                    "Node.js not found in PATH. Please install Node.js (v18+) "
                    "and ensure it's in your PATH."
                ),
            )

        # Check Node.js version
        # On Windows, use shell=True to ensure PATH is properly resolved
        use_shell = platform.system() == "Windows"
        node_version_output = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            check=True,
            shell=use_shell,
        ).stdout.strip()
        # Expecting vX.Y.Z, extract X
        node_major_version = int(node_version_output.split(".")[0].lstrip("v"))
        if node_major_version < 18:
            return (
                False,
                f"Node.js v18+ required, found {node_version_output}. Please upgrade Node.js.",
            )

        # Check npm version
        npm_cmd = shutil.which("npm")
        if not npm_cmd:
            return (
                False,
                "npm not found in PATH. Please install npm (comes with Node.js).",
            )

        npm_version_output = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            check=True,
            shell=use_shell,
        ).stdout.strip()

        return True, f"Node.js {node_version_output}, npm {npm_version_output}"
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return (
            False,
            f"Node.js or npm not found or not working: {e}. Please install Node.js (v18+) and npm.",
        )


def check_python_packages() -> Tuple[bool, Optional[str]]:
    """
    Check if required Python packages for the backend are installed.

    Returns:
        Tuple of (is_installed, status_message)
    """
    required_packages = ["fastapi", "uvicorn", "sqlalchemy", "pydantic"]
    missing = []
    for pkg in required_packages:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        return (
            False,
            f"Missing Python packages for backend: {', '.join(missing)}. "
            f"Run 'pip install -r dashboard/backend/requirements.txt'.",
        )
    return True, "All Python packages installed."


def check_ports(
    backend_port: int, frontend_port: int, backend_host: str
) -> Tuple[bool, Optional[str]]:
    """
    Check if required ports are available.

    Args:
        backend_port: Port for the backend API.
        frontend_port: Port for the frontend UI.
        backend_host: Host for the backend API.

    Returns:
        Tuple of (are_available, status_message)
    """
    ports_to_check = {
        backend_port: (backend_host, f"Backend API ({backend_host}:{backend_port})"),
        frontend_port: ("127.0.0.1", f"Frontend UI (localhost:{frontend_port})"),
    }
    unavailable = []

    for port, (host, name) in ports_to_check.items():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                # Try to bind to the port to see if it's available
                s.bind((host, port))
            except OSError:
                unavailable.append(name)

    if unavailable:
        return (
            False,
            f"Required ports are not available: {', '.join(unavailable)}. "
            f"Please free up these ports or specify different ones using "
            f"'--port-backend' and '--port-frontend'.",
        )
    return True, "All required ports are available."


def check_database_connection(config: BaselinrConfig) -> Tuple[bool, Optional[str]]:
    """
    Check if the database connection specified in BaselinrConfig is valid.

    Args:
        config: Baselinr configuration.

    Returns:
        Tuple of (is_connected, status_message)
    """
    try:
        # Use the existing connector factory to create an engine and test connection
        connector = create_connector(config.storage.connection, config.retry)
        with connector.engine.connect() as connection:
            # Simple query to test connection
            from sqlalchemy import text

            connection.execute(text("SELECT 1"))
        return True, "Database connection successful."
    except Exception as e:
        return (
            False,
            f"Failed to connect to the database: {e}. "
            f"Please check your 'storage.connection' settings in your config file.",
        )


def check_all_dependencies(
    config: BaselinrConfig, backend_port: int, frontend_port: int, backend_host: str
):
    """
    Run all dependency checks and raise DependencyError if any fail.

    Args:
        config: Baselinr configuration.
        backend_port: Port for the backend API.
        frontend_port: Port for the frontend UI.
        backend_host: Host for the backend API.

    Raises:
        DependencyError: If any dependency check fails.
    """
    logger.info("Running dependency checks for Baselinr UI...")

    # 1. Check Node.js and npm
    nodejs_ok, nodejs_msg = check_nodejs()
    if not nodejs_ok:
        raise DependencyError(f"Node.js/npm check failed: {nodejs_msg}")
    logger.info(f"Node.js/npm check: {nodejs_msg}")

    # 2. Check Python packages
    python_ok, python_msg = check_python_packages()
    if not python_ok:
        raise DependencyError(f"Python packages check failed: {python_msg}")
    logger.info(f"Python packages check: {python_msg}")

    # 3. Check ports
    ports_ok, ports_msg = check_ports(backend_port, frontend_port, backend_host)
    if not ports_ok:
        raise DependencyError(f"Port check failed: {ports_msg}")
    logger.info(f"Port check: {ports_msg}")

    # 4. Check database connection
    db_ok, db_msg = check_database_connection(config)
    if not db_ok:
        raise DependencyError(f"Database connection check failed: {db_msg}")
    logger.info(f"Database connection check: {db_msg}")

    logger.info("All Baselinr UI dependencies met.")

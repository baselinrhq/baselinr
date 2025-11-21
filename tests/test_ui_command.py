"""Tests for UI command."""

import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from baselinr.cli import ui_command
from baselinr.config.schema import BaselinrConfig, ConnectionConfig, DatabaseType, StorageConfig


@pytest.fixture
def sample_config():
    """Create a sample BaselinrConfig for testing."""
    source_config = ConnectionConfig(
        type=DatabaseType.POSTGRES,
        host="localhost",
        port=5432,
        database="testdb",
        username="testuser",
        password="testpass",
    )
    storage_config = StorageConfig(
        connection=ConnectionConfig(
            type=DatabaseType.POSTGRES,
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass",
        )
    )
    return BaselinrConfig(
        environment="test",
        source=source_config,
        storage=storage_config,
    )




def test_ui_command_basic(sample_config, tmp_path):
    """Test basic UI command execution."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("environment: test\n")

    with patch("baselinr.cli.ConfigLoader.load_from_file", return_value=sample_config):
        with patch("baselinr.ui.dependencies.check_all_dependencies") as mock_check:
            with patch("baselinr.ui.start_dashboard_foreground") as mock_start:
                args = MagicMock()
                args.config = str(config_file)
                args.port_backend = 8000
                args.port_frontend = 3000
                args.host = "0.0.0.0"

                result = ui_command(args)
                assert result == 0
                mock_check.assert_called_once()
                mock_start.assert_called_once_with(
                    sample_config, backend_port=8000, frontend_port=3000, backend_host="0.0.0.0"
                )


def test_ui_command_custom_ports(sample_config, tmp_path):
    """Test UI command with custom ports."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("environment: test\n")

    with patch("baselinr.cli.ConfigLoader.load_from_file", return_value=sample_config):
        with patch("baselinr.ui.dependencies.check_all_dependencies"):
            with patch("baselinr.ui.start_dashboard_foreground") as mock_start:
                args = MagicMock()
                args.config = str(config_file)
                args.port_backend = 8080
                args.port_frontend = 3001
                args.host = "127.0.0.1"

                result = ui_command(args)
                assert result == 0
                mock_start.assert_called_once_with(
                    sample_config, backend_port=8080, frontend_port=3001, backend_host="127.0.0.1"
                )


def test_ui_command_dependency_error(sample_config, tmp_path):
    """Test UI command handles dependency errors."""
    from baselinr.ui.dependencies import DependencyError

    config_file = tmp_path / "config.yml"
    config_file.write_text("environment: test\n")

    with patch("baselinr.cli.ConfigLoader.load_from_file", return_value=sample_config):
        with patch("baselinr.ui.check_all_dependencies", side_effect=DependencyError("Missing Node.js")):
            args = MagicMock()
            args.config = str(config_file)
            args.port_backend = 8000
            args.port_frontend = 3000
            args.host = "0.0.0.0"

            result = ui_command(args)
            assert result == 1


def test_ui_command_keyboard_interrupt(sample_config, tmp_path):
    """Test UI command handles KeyboardInterrupt gracefully."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("environment: test\n")

    with patch("baselinr.cli.ConfigLoader.load_from_file", return_value=sample_config):
        with patch("baselinr.ui.dependencies.check_all_dependencies"):
            # Mock start_dashboard_foreground to raise KeyboardInterrupt
            with patch("baselinr.ui.start_dashboard_foreground", side_effect=KeyboardInterrupt()):
                args = MagicMock()
                args.config = str(config_file)
                args.port_backend = 8000
                args.port_frontend = 3000
                args.host = "0.0.0.0"

                result = ui_command(args)
                assert result == 0


def test_ui_command_config_error(tmp_path):
    """Test UI command handles config loading errors."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("environment: test\n")

    with patch("baselinr.cli.ConfigLoader.load_from_file", side_effect=Exception("Config error")):
        args = MagicMock()
        args.config = str(config_file)
        args.port_backend = 8000
        args.port_frontend = 3000
        args.host = "0.0.0.0"

        result = ui_command(args)
        assert result == 1


def test_ui_command_startup_error(sample_config, tmp_path):
    """Test UI command handles startup errors."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("environment: test\n")

    with patch("baselinr.cli.ConfigLoader.load_from_file", return_value=sample_config):
        with patch("baselinr.ui.dependencies.check_all_dependencies"):
            with patch("baselinr.ui.start_dashboard_foreground", side_effect=RuntimeError("Startup failed")):
                args = MagicMock()
                args.config = str(config_file)
                args.port_backend = 8000
                args.port_frontend = 3000
                args.host = "0.0.0.0"

                result = ui_command(args)
                assert result == 1


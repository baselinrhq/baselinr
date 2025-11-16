"""Pytest configuration for ProfileMesh tests."""

import os
import sys
import tempfile

# Set up Airflow environment variables BEFORE any imports
# This must happen before airflow modules are imported

# Airflow 2.8+ requires absolute path for SQLite, not :memory:
# Use a temporary file that will be cleaned up
AIRFLOW_DB_PATH = os.path.join(tempfile.gettempdir(), 'airflow_test.db')

os.environ.setdefault('AIRFLOW__CORE__DAGS_FOLDER', '/tmp/airflow_dags')
os.environ.setdefault('AIRFLOW__CORE__PLUGINS_FOLDER', '/tmp/airflow_plugins')
os.environ.setdefault('AIRFLOW__CORE__LOAD_EXAMPLES', 'False')
os.environ.setdefault('AIRFLOW__CORE__UNIT_TEST_MODE', 'True')
os.environ.setdefault('AIRFLOW__DATABASE__SQL_ALCHEMY_CONN', f'sqlite:///{AIRFLOW_DB_PATH}')
os.environ.setdefault('AIRFLOW__CORE__EXECUTOR', 'SequentialExecutor')
os.environ.setdefault('AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION', 'False')

# Disable Airflow's complex logging configuration in tests
os.environ.setdefault('AIRFLOW__LOGGING__LOGGING_CONFIG_CLASS', '')

# Create required directories
os.makedirs('/tmp/airflow_dags', exist_ok=True)
os.makedirs('/tmp/airflow_plugins', exist_ok=True)
os.makedirs('/tmp/airflow_logs', exist_ok=True)

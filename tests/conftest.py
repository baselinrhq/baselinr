"""Pytest configuration for ProfileMesh tests."""

import os
import sys

# Set up Airflow environment variables BEFORE any imports
# This must happen before airflow modules are imported
os.environ.setdefault('AIRFLOW__CORE__DAGS_FOLDER', '/tmp/airflow_dags')
os.environ.setdefault('AIRFLOW__CORE__PLUGINS_FOLDER', '/tmp/airflow_plugins')
os.environ.setdefault('AIRFLOW__CORE__LOAD_EXAMPLES', 'False')
os.environ.setdefault('AIRFLOW__CORE__UNIT_TEST_MODE', 'True')
os.environ.setdefault('AIRFLOW__DATABASE__SQL_ALCHEMY_CONN', 'sqlite:///:memory:')
os.environ.setdefault('AIRFLOW__CORE__EXECUTOR', 'SequentialExecutor')
os.environ.setdefault('AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION', 'False')

# Disable Airflow's complex logging configuration in tests
os.environ.setdefault('AIRFLOW__LOGGING__LOGGING_CONFIG_CLASS', '')

# Create required directories
os.makedirs('/tmp/airflow_dags', exist_ok=True)
os.makedirs('/tmp/airflow_plugins', exist_ok=True)
os.makedirs('/tmp/airflow_logs', exist_ok=True)

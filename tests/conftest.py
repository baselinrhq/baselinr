"""Pytest configuration for ProfileMesh tests."""

import os
import sys
import tempfile
import logging

# Set up Airflow environment variables BEFORE any imports
# This must happen before airflow modules are imported

# Airflow 2.8+ requires absolute path for SQLite, not :memory:
# Use a temporary file that will be cleaned up
AIRFLOW_DB_PATH = os.path.join(tempfile.gettempdir(), 'airflow_test.db')
AIRFLOW_HOME = os.path.join(tempfile.gettempdir(), 'airflow_home_test')

os.environ.setdefault('AIRFLOW_HOME', AIRFLOW_HOME)
os.environ.setdefault('AIRFLOW__CORE__DAGS_FOLDER', os.path.join(AIRFLOW_HOME, 'dags'))
os.environ.setdefault('AIRFLOW__CORE__PLUGINS_FOLDER', os.path.join(AIRFLOW_HOME, 'plugins'))
os.environ.setdefault('AIRFLOW__CORE__LOAD_EXAMPLES', 'False')
os.environ.setdefault('AIRFLOW__CORE__UNIT_TEST_MODE', 'True')
os.environ.setdefault('AIRFLOW__DATABASE__SQL_ALCHEMY_CONN', f'sqlite:///{AIRFLOW_DB_PATH}')
os.environ.setdefault('AIRFLOW__CORE__EXECUTOR', 'SequentialExecutor')
os.environ.setdefault('AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION', 'False')

# Disable colored logs and set minimal logging
os.environ.setdefault('AIRFLOW__LOGGING__COLORED_CONSOLE_LOG', 'False')
os.environ.setdefault('AIRFLOW__LOGGING__COLORED_LOG_FORMAT', '%(message)s')
os.environ.setdefault('AIRFLOW__LOGGING__COLORED_FORMATTER_CLASS', 'logging.Formatter')
os.environ.setdefault('AIRFLOW__LOGGING__LOG_FORMAT', '%(message)s')

# Create required directories
os.makedirs(os.path.join(AIRFLOW_HOME, 'dags'), exist_ok=True)
os.makedirs(os.path.join(AIRFLOW_HOME, 'plugins'), exist_ok=True)
os.makedirs(os.path.join(AIRFLOW_HOME, 'logs'), exist_ok=True)

# Create a minimal airflow.cfg to prevent Airflow from trying to create one
_airflow_cfg = os.path.join(AIRFLOW_HOME, 'airflow.cfg')
if not os.path.exists(_airflow_cfg):
    with open(_airflow_cfg, 'w') as f:
        f.write(f'''[core]
dags_folder = {os.path.join(AIRFLOW_HOME, 'dags')}
plugins_folder = {os.path.join(AIRFLOW_HOME, 'plugins')}
executor = SequentialExecutor
load_examples = False
unit_test_mode = True

[database]
sql_alchemy_conn = sqlite:///{AIRFLOW_DB_PATH}

[logging]
logging_level = CRITICAL
fab_logging_level = CRITICAL
colored_console_log = False
''')

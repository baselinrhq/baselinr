# Baselinr Installation Guide

## Prerequisites

Before installing Baselinr, ensure you have:

- **Python 3.10 or higher**
  ```bash
  python --version  # Should be 3.10+
  ```

- **pip** (Python package manager)
  ```bash
  pip --version
  ```

- **Docker and Docker Compose** (optional, for development environment)
  ```bash
  docker --version
  docker-compose --version
  ```

## Installation Options

### Option 1: Basic Installation (PostgreSQL Only)

For profiling PostgreSQL databases:

```bash
cd profile_mesh
pip install -e .
```

This installs:
- Core Baselinr
- PostgreSQL support
- SQLite support
- Configuration management
- CLI interface

### Option 2: With Dagster Orchestration

For Dagster integration:

```bash
pip install -e ".[dagster]"
```

Adds:
- Dagster asset factory
- Job scheduling
- Web UI
- Event emission

### Option 3: With Snowflake Support

For Snowflake data warehouses:

```bash
pip install -e ".[snowflake]"
```

Adds:
- Snowflake connector
- Snowflake-specific optimizations

### Option 4: Full Installation (Recommended for Development)

Install everything:

```bash
pip install -e ".[all,dev]"
```

Includes:
- All database connectors
- Dagster integration
- Development tools (pytest, black, mypy)
- Full feature set

## Verify Installation

After installation, verify Baselinr is working:

```bash
# Check CLI is available
baselinr --help

# Check Python import
python -c "from baselinr import __version__; print(__version__)"
```

You should see:
```
Baselinr - Data profiling and drift detection
...
```

## Post-Installation Setup

### 1. Set Up Development Database (Optional)

Start the Docker environment with PostgreSQL and Dagster:

```bash
cd profile_mesh
make docker-up
```

Wait about 30 seconds for initialization, then verify:

```bash
# Check PostgreSQL
docker exec -it baselinr_postgres psql -U baselinr -d baselinr -c "\dt"

# Check Dagster UI
# Open http://localhost:3000 in your browser
```

### 2. Create Configuration

Copy the example configuration:

```bash
cp examples/config.yml my_config.yml
```

Edit `my_config.yml` with your database credentials:

```yaml
source:
  type: postgres  # or snowflake, sqlite
  host: your-database-host
  port: 5432
  database: your-database
  username: your-username
  password: your-password
```

### 3. Run First Profile

```bash
baselinr profile --config my_config.yml
```

## Troubleshooting

### "Command not found: baselinr"

The CLI wasn't installed correctly. Try:

```bash
pip install --force-reinstall -e .
```

Or use the Python module directly:

```bash
python -m baselinr.cli profile --config config.yml
```

### "ModuleNotFoundError: No module named 'baselinr'"

The package isn't in your Python path. Make sure you're in the `profile_mesh` directory and run:

```bash
pip install -e .
```

### "Connection refused" with Docker

Docker containers may not be ready:

```bash
# Check container status
docker ps

# View logs
cd docker && docker-compose logs postgres

# Restart containers
make docker-down
make docker-up
```

### "pydantic.errors.ValidationError"

Your configuration file has errors. Check:
- YAML syntax (indentation)
- Required fields are present
- Database type is valid (postgres, snowflake, sqlite)

Run with debug logging:

```bash
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from baselinr.config.loader import ConfigLoader
ConfigLoader.load_from_file('my_config.yml')
"
```

### Snowflake Connection Issues

Make sure you have the Snowflake connector installed:

```bash
pip install -e ".[snowflake]"
```

Verify your Snowflake config includes:
- account
- warehouse
- role (optional but recommended)

### Permission Errors (Windows)

If you get permission errors installing:

```bash
# Run PowerShell as Administrator, or use --user flag
pip install --user -e .
```

## Environment Variables

Baselinr supports environment variable overrides:

```bash
# Set environment-specific values
export BASELINR_SOURCE__HOST=prod-server.example.com
export BASELINR_SOURCE__PASSWORD=secret_password
export BASELINR_ENVIRONMENT=production

# Run with overrides
baselinr profile --config config.yml
```

## Upgrading

To upgrade to a newer version:

```bash
cd profile_mesh
git pull  # If using git
pip install --upgrade -e ".[all]"
```

## Uninstalling

To remove Baselinr:

```bash
pip uninstall baselinr

# Also remove Docker environment if you set it up
cd docker
docker-compose down -v  # -v removes volumes
```

## Next Steps

After successful installation:

1. **Read [QUICKSTART.md](QUICKSTART.md)** for a guided tutorial
2. **Run the quickstart example**: `python examples/quickstart.py`
3. **Check the README.md** for full documentation
4. **Explore Dagster integration** at http://localhost:3000 (if using Docker)

## Getting Help

If you encounter issues:

1. Check this troubleshooting section
2. Review the error message carefully
3. Check Docker logs: `docker-compose logs`
4. Verify your configuration file
5. Try the SQLite example first (no external database needed)

## System Requirements

### Minimum
- Python 3.10+
- 100 MB disk space
- 512 MB RAM

### Recommended
- Python 3.11+
- 500 MB disk space (with Docker images)
- 2 GB RAM (for Dagster)
- Docker Desktop (for development)

## Platform Support

Baselinr is tested on:
- ✅ Linux (Ubuntu 20.04+)
- ✅ macOS (11+)
- ✅ Windows 10/11 (with WSL2 recommended for Docker)

---

For more information, see:
- **README.md** - Main documentation
- **[QUICKSTART.md](QUICKSTART.md)** - Getting started guide
- **DEVELOPMENT.md** - Developer guide


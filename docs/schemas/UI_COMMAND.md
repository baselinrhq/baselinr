# Baselinr UI Command

The `baselinr ui` command starts the Baselinr Quality Studio in **foreground mode**. It launches both the backend API (FastAPI) and frontend UI (Next.js) in your current terminal, providing a no-code web interface for configuring and managing your data quality setup, as well as viewing profiling runs, drift alerts, and metrics.

This command is an alternative to manually running `dashboard/backend/start.sh` and `dashboard/frontend/start.sh` in separate terminals. It automatically configures the Quality Studio to use your Baselinr configuration file's database connection.

## Usage

```bash
baselinr ui --config config.yml [OPTIONS]
```

## Options

*   `--config, -c` (required): Path to your Baselinr configuration file (YAML or JSON). The Quality Studio will use the `storage.connection` settings from this file to connect to the database.
*   `--port-backend` (default: 8000): Port for the backend API server.
*   `--port-frontend` (default: 3000): Port for the frontend UI server.
*   `--host` (default: "0.0.0.0"): Host address for the backend API server. Use "127.0.0.1" to bind only to localhost.

## Examples

### Basic Usage

```bash
baselinr ui --config examples/config.yml
```

Starts the Quality Studio with default ports (backend on 8000, frontend on 3000).

### Custom Ports

```bash
baselinr ui --config examples/config.yml --port-backend 8080 --port-frontend 3001
```

Starts the Quality Studio with custom ports.

### Localhost Only

```bash
baselinr ui --config examples/config.yml --host 127.0.0.1
```

Binds the backend API only to localhost (not accessible from other machines).

## How It Works

1. **Dependency Checks**: The command first verifies that all required dependencies are installed:
   * Node.js (v18+) and npm (for the frontend)
   * Python packages: FastAPI, uvicorn, sqlalchemy, pydantic (for the backend)
   * Port availability (backend and frontend ports must be free)
   * Database connection (tests connection using your config file)

2. **Configuration**: Builds a database connection string from your Baselinr config file's `storage.connection` settings. The Quality Studio currently supports PostgreSQL and SQLite.

3. **Process Startup**: Starts both processes in the foreground:
   * Backend: Runs `python main.py` in `dashboard/backend/` with `BASELINR_DB_URL` environment variable set
   * Frontend: Runs `npm run dev` in `dashboard/frontend/` with `NEXT_PUBLIC_API_URL` and `PORT` environment variables set

4. **Signal Handling**: Press `Ctrl+C` to gracefully shut down both processes.

## Requirements

### Node.js and npm

The frontend requires Node.js v18 or higher and npm. Install from [nodejs.org](https://nodejs.org/).

### Python Packages

The backend requires several Python packages. Install them with:

```bash
pip install -r dashboard/backend/requirements.txt
```

### Database

The Quality Studio requires a PostgreSQL or SQLite database. The connection is configured via your Baselinr config file's `storage.connection` section.

## Troubleshooting

### "Node.js/npm check failed"

Install Node.js v18+ from [nodejs.org](https://nodejs.org/). Verify installation:

```bash
node --version
npm --version
```

### "Python packages check failed"

Install the required packages:

```bash
pip install -r dashboard/backend/requirements.txt
```

### "Port check failed"

One or both ports (backend/frontend) are already in use. Either:
* Stop the process using those ports
* Use different ports with `--port-backend` and `--port-frontend`

### "Database connection check failed"

Verify your `storage.connection` settings in your config file are correct. The dashboard currently only supports PostgreSQL and SQLite.

### Backend or Frontend Fails to Start

Check the terminal output for error messages. Common issues:
* Missing dependencies (install Node.js packages with `npm install` in `dashboard/frontend/`)
* Database connection issues (verify `BASELINR_DB_URL` is correct)
* Port conflicts (use `--port-backend` and `--port-frontend` to change ports)

## Differences from Manual Startup

The `baselinr ui` command provides these advantages over manually running the start scripts:

1. **Automatic Configuration**: Reads database connection from your Baselinr config file automatically
2. **Dependency Checking**: Verifies all requirements before starting
3. **Port Management**: Checks port availability and allows custom ports
4. **Unified Control**: Start and stop both processes with a single command
5. **Better Error Messages**: Provides clear error messages if dependencies are missing

## Related Documentation

*   [CLI Query Examples](./QUERY_EXAMPLES.md) - Other CLI query commands
*   [Status Command](./STATUS_COMMAND.md) - CLI-based status dashboard
*   [Dashboard Quick Start](../dashboard/QUICKSTART.md) - Manual dashboard setup (alternative to `baselinr ui`)



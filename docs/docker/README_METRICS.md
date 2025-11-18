# Prometheus & Grafana Setup for Baselinr

This directory contains the configuration for Prometheus and Grafana to monitor Baselinr metrics.

## Quick Start

1. **Start Baselinr with metrics enabled** (on your host machine):
   ```bash
   baselinr profile --config examples/config.yml
   ```
   Make sure `monitoring.enable_metrics: true` and `monitoring.keep_alive: true` in your config.

2. **Start the monitoring stack**:
   ```bash
   cd docker
   docker compose up -d prometheus grafana
   ```

3. **Access the services**:
   - **Grafana**: http://localhost:3001 (username: `admin`, password: `admin`)
   - **Prometheus**: http://localhost:9090
   - **Baselinr Metrics**: http://localhost:9753/metrics

## Importing the Dashboard

1. Open Grafana at http://localhost:3001
2. Login with `admin` / `admin`
3. Go to **Dashboards** → **Import**
4. Click **Upload JSON file**
5. Select `docker/grafana-dashboards/baselinr-dashboard.json`
6. Click **Import**

The dashboard will automatically show metrics once Prometheus starts scraping.

## Verifying Prometheus is Scraping

1. Open Prometheus at http://localhost:9090
2. Go to **Status** → **Targets**
3. You should see `baselinr` target with status **UP**

If the target shows as **DOWN**, check:
- Is Baselinr running with metrics enabled?
- Can you access http://localhost:9753/metrics from your browser?
- On Linux, you may need to change `host.docker.internal` to your host IP in `prometheus.yml`

## Troubleshooting

### Prometheus can't reach Baselinr

**On Windows/Mac**: `host.docker.internal` should work automatically.

**On Linux**: You may need to:
1. Find your host IP: `ip addr show docker0` or `hostname -I`
2. Update `prometheus.yml` to use that IP instead of `host.docker.internal`
3. Or add `network_mode: host` to the prometheus service (Linux only)

### No metrics showing in Grafana

1. Check Prometheus targets: http://localhost:9090/targets
2. Check if metrics exist: http://localhost:9090/graph?g0.expr=baselinr_profile_runs_total
3. Verify Baselinr is running and metrics endpoint is accessible
4. Check Grafana datasource is connected: **Configuration** → **Data Sources** → **Prometheus**

### Port conflicts

- Grafana uses port **3001** (to avoid conflict with Dagster on 3000)
- Prometheus uses port **9090**
- Baselinr metrics uses port **9753**

Change ports in `docker-compose.yml` if needed.

## Files

- `prometheus.yml` - Prometheus configuration (scrape targets, intervals)
- `grafana-datasources.yml` - Auto-configures Prometheus as Grafana datasource
- `grafana-dashboards/baselinr-dashboard.json` - Pre-built Baselinr dashboard

## Stopping the Stack

```bash
docker compose down
```

To also remove volumes (clears Prometheus and Grafana data):
```bash
docker compose down -v
```


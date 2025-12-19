/**
 * Demo Data Service for Cloudflare Pages Functions
 * Loads and filters pre-generated JSON demo data
 */

interface FilterOptions {
  warehouse?: string;
  schema?: string;
  table?: string;
  status?: string;
  severity?: string;
  search?: string;
  hasDrift?: boolean;
  hasFailedValidations?: boolean;
  startDate?: Date;
  endDate?: Date;
  minDuration?: number;
  maxDuration?: number;
  sortBy?: string;
  sortOrder?: string;
  limit?: number;
  offset?: number;
  page?: number;
  pageSize?: number;
}

class DemoDataService {
  private dataLoaded = false;
  private loadPromise: Promise<void> | null = null;

  // Data storage
  public runs: any[] = [];
  public metrics: any[] = [];
  public driftEvents: any[] = [];
  public tables: any[] = [];
  public validationResults: any[] = [];
  public metadataData: any = null;

  /**
   * Load demo data from JSON files
   */
  async loadData(baseUrl: string): Promise<void> {
    if (this.dataLoaded) {
      return;
    }

    if (this.loadPromise) {
      return this.loadPromise;
    }

    this.loadPromise = this._loadDataInternal(baseUrl);
    await this.loadPromise;
  }

  private async _loadDataInternal(baseUrl: string): Promise<void> {
    try {
      // Validate baseUrl
      if (baseUrl === undefined || baseUrl === null) {
        throw new Error(`baseUrl is ${baseUrl === undefined ? 'undefined' : 'null'}`);
      }
      if (typeof baseUrl !== 'string') {
        throw new Error(`Invalid baseUrl type: ${typeof baseUrl}, value: ${JSON.stringify(baseUrl)}`);
      }
      if (baseUrl.trim() === '') {
        throw new Error('baseUrl is an empty string');
      }

      // Validate that baseUrl is a valid URL
      let validatedBaseUrl: URL;
      try {
        validatedBaseUrl = new URL(baseUrl);
      } catch (urlError) {
        const errorMsg = urlError instanceof Error ? urlError.message : String(urlError);
        // Include baseUrl in error for debugging, but safely escape it
        const safeBaseUrl = baseUrl.replace(/"/g, '\\"');
        throw new Error(`Invalid URL: baseUrl="${safeBaseUrl}", error="${errorMsg}"`);
      }

      // Helper function to safely construct and fetch JSON URLs
      const fetchJson = async (path: string, defaultValue: any = []) => {
        try {
          // Construct full URL using URL constructor to ensure it's valid
          let fullUrl: string;
          try {
            // Use URL constructor to properly join baseUrl and path
            const url = new URL(path, validatedBaseUrl.toString());
            fullUrl = url.toString();
          } catch (urlError) {
            console.error(`Error constructing URL for ${path} with base ${validatedBaseUrl}:`, urlError);
            return defaultValue;
          }

          const response = await fetch(fullUrl);
          if (!response.ok) {
            console.warn(`Failed to fetch ${fullUrl}: ${response.status} ${response.statusText}`);
            return defaultValue;
          }
          return await response.json();
        } catch (error) {
          console.error(`Error fetching ${path}:`, error);
          return defaultValue;
        }
      };

      // Load all JSON files in parallel
      const [runsData, metricsData, driftData, tablesData, validationData, metadataData] = await Promise.all([
        fetchJson('runs.json', []),
        fetchJson('metrics.json', []),
        fetchJson('drift_events.json', []),
        fetchJson('tables.json', []),
        fetchJson('validation_results.json', []),
        fetchJson('metadata.json', null),
      ]);

      this.runs = Array.isArray(runsData) ? runsData : [];
      this.metrics = Array.isArray(metricsData) ? metricsData : [];
      this.driftEvents = Array.isArray(driftData) ? driftData : [];
      this.tables = Array.isArray(tablesData) ? tablesData : [];
      this.validationResults = Array.isArray(validationData) ? validationData : [];
      this.metadataData = metadataData;
      this.dataLoaded = true;
    } catch (error) {
      console.error('Error loading demo data:', error);
      // Initialize with empty arrays if loading fails
      this.runs = [];
      this.metrics = [];
      this.driftEvents = [];
      this.tables = [];
      this.validationResults = [];
      this.metadataData = null;
      throw error;
    }
  }

  /**
   * Get runs with filtering
   */
  async getRuns(filters: FilterOptions): Promise<any[]> {
    let filtered = [...this.runs];

    if (filters.warehouse) {
      filtered = filtered.filter(r => r.warehouse_type === filters.warehouse);
    }
    if (filters.schema) {
      filtered = filtered.filter(r => r.schema_name === filters.schema);
    }
    if (filters.table) {
      filtered = filtered.filter(r => r.dataset_name === filters.table);
    }
    if (filters.status) {
      filtered = filtered.filter(r => r.status === filters.status);
    }
    if (filters.startDate) {
      filtered = filtered.filter(r => new Date(r.profiled_at) >= filters.startDate!);
    }
    if (filters.endDate) {
      filtered = filtered.filter(r => new Date(r.profiled_at) <= filters.endDate!);
    }

    // Sort
    const sortBy = filters.sortBy || 'profiled_at';
    const sortOrder = filters.sortOrder || 'desc';
    filtered.sort((a, b) => {
      const aVal = a[sortBy];
      const bVal = b[sortBy];
      const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sortOrder === 'desc' ? -comparison : comparison;
    });

    // Paginate
    const offset = filters.offset || 0;
    const limit = filters.limit || 100;
    return filtered.slice(offset, offset + limit);
  }

  /**
   * Get drift alerts with filtering
   */
  async getDriftAlerts(filters: FilterOptions): Promise<any[]> {
    let filtered = [...this.driftEvents];

    if (filters.warehouse) {
      filtered = filtered.filter(d => d.warehouse_type === filters.warehouse);
    }
    if (filters.schema) {
      filtered = filtered.filter(d => d.schema_name === filters.schema);
    }
    if (filters.table) {
      filtered = filtered.filter(d => d.table_name === filters.table);
    }
    if (filters.severity) {
      filtered = filtered.filter(d => (d.severity || d.drift_severity) === filters.severity);
    }
    if (filters.startDate) {
      filtered = filtered.filter(d => new Date(d.timestamp) >= filters.startDate!);
    }
    if (filters.endDate) {
      filtered = filtered.filter(d => new Date(d.timestamp) <= filters.endDate!);
    }

    // Sort
    const sortBy = filters.sortBy || 'timestamp';
    const sortOrder = filters.sortOrder || 'desc';
    filtered.sort((a, b) => {
      const aVal = a[sortBy];
      const bVal = b[sortBy];
      const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sortOrder === 'desc' ? -comparison : comparison;
    });

    // Paginate
    const offset = filters.offset || 0;
    const limit = filters.limit || 100;
    return filtered.slice(offset, offset + limit);
  }

  /**
   * Get tables with filtering
   */
  async getTables(filters: FilterOptions): Promise<{ tables: any[]; total: number; page: number; pageSize: number }> {
    let filtered = [...this.tables];

    if (filters.warehouse) {
      filtered = filtered.filter(t => t.warehouse_type === filters.warehouse);
    }
    if (filters.schema) {
      filtered = filtered.filter(t => t.schema_name === filters.schema);
    }
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(t => 
        t.table_name?.toLowerCase().includes(searchLower) ||
        t.schema_name?.toLowerCase().includes(searchLower)
      );
    }

    // Sort
    const sortBy = filters.sortBy || 'table_name';
    const sortOrder = filters.sortOrder || 'asc';
    filtered.sort((a, b) => {
      const aVal = a[sortBy];
      const bVal = b[sortBy];
      const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sortOrder === 'desc' ? -comparison : comparison;
    });

    const total = filtered.length;
    const page = filters.page || 1;
    const pageSize = filters.pageSize || 50;
    const offset = (page - 1) * pageSize;
    const tables = filtered.slice(offset, offset + pageSize);

    return { tables, total, page, pageSize };
  }

  /**
   * Get warehouses
   */
  async getWarehouses(): Promise<any[]> {
    const warehouses = new Set<string>();
    this.runs.forEach(run => {
      if (run.warehouse_type) {
        warehouses.add(run.warehouse_type);
      }
    });
    return Array.from(warehouses).map(w => ({ warehouse_type: w }));
  }

  /**
   * Get validation summary
   */
  async getValidationSummary(filters: FilterOptions): Promise<any> {
    // Basic implementation - can be enhanced
    const passed = this.validationResults.filter(v => v.passed === true || v.status === 'pass').length;
    const failed = this.validationResults.filter(v => v.passed === false || v.status === 'fail').length;
    
    return {
      total_validations: this.validationResults.length,
      passed,
      failed,
    };
  }

  /**
   * Get validation results list
   */
  async getValidationResultsList(filters: FilterOptions): Promise<any> {
    let filtered = [...this.validationResults];

    if (filters.warehouse) {
      filtered = filtered.filter(v => v.warehouse_type === filters.warehouse);
    }
    if (filters.table) {
      filtered = filtered.filter(v => v.table_name === filters.table);
    }

    const offset = filters.offset || 0;
    const limit = filters.limit || 100;
    return filtered.slice(offset, offset + limit);
  }

  /**
   * Get table validation results
   */
  async getTableValidationResults(tableName: string, schema?: string, limit?: number): Promise<any[]> {
    let filtered = this.validationResults.filter(v => v.table_name === tableName);
    if (schema) {
      filtered = filtered.filter(v => v.schema_name === schema);
    }
    return filtered.slice(0, limit || 100);
  }

  /**
   * Get table overview
   */
  async getTableOverview(tableName: string, schema?: string, warehouse?: string): Promise<any> {
    // Basic implementation - combine runs, metrics, drift for a table
    const tableRuns = this.runs.filter(r => {
      return r.dataset_name === tableName &&
        (!schema || r.schema_name === schema) &&
        (!warehouse || r.warehouse_type === warehouse);
    });

    return {
      table_name: tableName,
      schema_name: schema,
      warehouse_type: warehouse,
      total_runs: tableRuns.length,
      recent_runs: tableRuns.slice(0, 10),
    };
  }

  /**
   * Get dashboard metrics
   */
  async getDashboardMetrics(filters: FilterOptions): Promise<any> {
    // Filter runs based on warehouse and startDate
    let filteredRuns = [...this.runs];
    if (filters.warehouse) {
      filteredRuns = filteredRuns.filter(r => r.warehouse_type === filters.warehouse);
    }
    if (filters.startDate) {
      filteredRuns = filteredRuns.filter(r => new Date(r.profiled_at) >= filters.startDate!);
    }

    // Count totals
    const totalRuns = filteredRuns.length;
    const totalTables = this.tables.length;
    const totalDriftEvents = this.driftEvents.length;

    // Calculate average row count
    const rowCounts = filteredRuns.map(r => r.row_count).filter((rc): rc is number => typeof rc === 'number');
    const avgRowCount = rowCounts.length > 0 
      ? rowCounts.reduce((sum, rc) => sum + rc, 0) / rowCounts.length 
      : 0;

    // Warehouse breakdown
    const warehouseBreakdown: Record<string, number> = {};
    filteredRuns.forEach(run => {
      const wh = run.warehouse_type || 'unknown';
      warehouseBreakdown[wh] = (warehouseBreakdown[wh] || 0) + 1;
    });

    // Calculate KPIs
    const successfulRuns = filteredRuns.filter(r => ['completed', 'success'].includes(r.status)).length;
    const successRate = totalRuns > 0 ? (successfulRuns / totalRuns * 100) : 0;

    const kpis = [
      { name: 'Success Rate', value: `${successRate.toFixed(1)}%`, trend: 'stable' },
      { name: 'Avg Row Count', value: Math.round(avgRowCount).toString(), trend: 'stable' },
      { name: 'Total Tables', value: totalTables, trend: 'stable' },
    ];

    // Generate run trend (last 30 days)
    const now = new Date();
    const thirtyDaysAgo = new Date(now);
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const runTrend = [];
    for (let i = 0; i < 30; i++) {
      const date = new Date(thirtyDaysAgo);
      date.setDate(date.getDate() + i);
      const dateStr = date.toISOString().split('T')[0];
      const count = filteredRuns.filter(r => {
        const profiledDate = new Date(r.profiled_at).toISOString().split('T')[0];
        return profiledDate === dateStr;
      }).length;
      runTrend.push({ timestamp: date.toISOString(), value: count });
    }

    // Generate drift trend (last 30 days)
    const driftTrend = [];
    for (let i = 0; i < 30; i++) {
      const date = new Date(thirtyDaysAgo);
      date.setDate(date.getDate() + i);
      const dateStr = date.toISOString().split('T')[0];
      const count = this.driftEvents.filter(e => {
        const eventDate = new Date(e.timestamp).toISOString().split('T')[0];
        return eventDate === dateStr;
      }).length;
      driftTrend.push({ timestamp: date.toISOString(), value: count });
    }

    // Get recent runs
    const recentRuns = await this.getRuns({
      warehouse: filters.warehouse,
      startDate: filters.startDate,
      limit: 10,
      offset: 0,
      sortBy: 'profiled_at',
      sortOrder: 'desc',
    });

    // Get recent drift
    const recentDrift = await this.getDriftAlerts({
      limit: 10,
      offset: 0,
      sortBy: 'timestamp',
      sortOrder: 'desc',
    });

    // Validation metrics
    const totalValidations = this.validationResults.length;
    const passedValidations = this.validationResults.filter(v => v.passed === true || v.status === 'pass').length;
    const validationPassRate = totalValidations > 0 ? (passedValidations / totalValidations * 100) : null;
    const failedValidationRules = totalValidations - passedValidations;

    // Validation trend
    const validationTrend = [];
    for (let i = 0; i < 30; i++) {
      const date = new Date(thirtyDaysAgo);
      date.setDate(date.getDate() + i);
      const dateStr = date.toISOString().split('T')[0];
      const dayValidations = this.validationResults.filter(v => {
        const validatedDate = new Date(v.validated_at).toISOString().split('T')[0];
        return validatedDate === dateStr;
      });
      if (dayValidations.length > 0) {
        const dayPassed = dayValidations.filter(v => v.passed === true || v.status === 'pass').length;
        const passRate = (dayPassed / dayValidations.length * 100);
        validationTrend.push({ timestamp: date.toISOString(), value: passRate });
      }
    }

    // System quality score
    const systemQualityScore = validationPassRate !== null ? validationPassRate : 85.0;
    const qualityScoreStatus = systemQualityScore >= 80 ? 'healthy' : systemQualityScore >= 60 ? 'warning' : 'critical';

    return {
      total_runs: totalRuns,
      total_tables: totalTables,
      total_drift_events: totalDriftEvents,
      avg_row_count: avgRowCount,
      kpis,
      run_trend: runTrend,
      drift_trend: driftTrend,
      warehouse_breakdown: warehouseBreakdown,
      recent_runs: recentRuns,
      recent_drift: recentDrift,
      validation_pass_rate: validationPassRate,
      total_validation_rules: totalValidations,
      failed_validation_rules: failedValidationRules,
      active_alerts: totalDriftEvents,
      data_freshness_hours: null,
      stale_tables_count: 0,
      validation_trend: validationTrend,
      system_quality_score: systemQualityScore,
      quality_score_status: qualityScoreStatus,
      quality_trend: null,
    };
  }

  /**
   * Get table metrics
   */
  async getTableMetrics(tableName: string, schema?: string, warehouse?: string): Promise<any> {
    // Find table
    let tableData = this.tables.find(t => 
      t.table_name === tableName &&
      (!schema || t.schema_name === schema) &&
      (!warehouse || t.warehouse_type === warehouse)
    );

    if (!tableData) {
      return null;
    }

    // Get runs for this table
    const tableRuns = this.runs.filter(r => 
      r.dataset_name === tableName &&
      (!schema || r.schema_name === schema) &&
      (!warehouse || r.warehouse_type === warehouse)
    );

    // Get metrics for this table
    const tableMetrics = this.metrics.filter(m => {
      const run = this.runs.find(r => r.run_id === m.run_id);
      return run && 
        run.dataset_name === tableName &&
        (!schema || run.schema_name === schema) &&
        (!warehouse || run.warehouse_type === warehouse);
    });

    // Get drift events for this table
    const tableDriftEvents = this.driftEvents.filter(e => 
      e.table_name === tableName &&
      (!schema || e.schema_name === schema) &&
      (!warehouse || e.warehouse_type === warehouse)
    );

    // Get columns grouped by column_name
    const columnsMap = new Map<string, any>();
    tableMetrics.forEach(metric => {
      const colName = metric.column_name;
      if (!columnsMap.has(colName)) {
        columnsMap.set(colName, {
          column_name: colName,
          column_type: metric.column_type,
          null_count: metric.null_count,
          null_percent: metric.null_percent,
          distinct_count: metric.distinct_count,
          distinct_percent: metric.distinct_percent,
          min_value: metric.min_value,
          max_value: metric.max_value,
          mean: metric.mean,
          stddev: metric.stddev,
          histogram: metric.histogram,
        });
      } else {
        // Use latest metric values
        const existing = columnsMap.get(colName)!;
        if (metric.null_count !== undefined) existing.null_count = metric.null_count;
        if (metric.null_percent !== undefined) existing.null_percent = metric.null_percent;
        if (metric.distinct_count !== undefined) existing.distinct_count = metric.distinct_count;
        if (metric.distinct_percent !== undefined) existing.distinct_percent = metric.distinct_percent;
        if (metric.min_value !== undefined) existing.min_value = metric.min_value;
        if (metric.max_value !== undefined) existing.max_value = metric.max_value;
        if (metric.mean !== undefined) existing.mean = metric.mean;
        if (metric.stddev !== undefined) existing.stddev = metric.stddev;
        if (metric.histogram !== undefined) existing.histogram = metric.histogram;
      }
    });

    const columns = Array.from(columnsMap.values());

    // Generate trends (last 30 days)
    const now = new Date();
    const thirtyDaysAgo = new Date(now);
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const rowCountTrend = [];
    const nullPercentTrend = [];
    const avgNullPercent = columns.reduce((sum, col) => sum + (col.null_percent || 0), 0) / (columns.length || 1);

    for (let i = 0; i < 30; i++) {
      const date = new Date(thirtyDaysAgo);
      date.setDate(date.getDate() + i);
      const dateStr = date.toISOString().split('T')[0];
      
      // Find run for this date
      const dayRun = tableRuns.find(r => {
        const runDate = new Date(r.profiled_at).toISOString().split('T')[0];
        return runDate === dateStr;
      });
      
      if (dayRun) {
        rowCountTrend.push({ timestamp: date.toISOString(), value: dayRun.row_count || 0 });
      } else {
        // Use last known value or 0
        const lastValue = rowCountTrend.length > 0 ? rowCountTrend[rowCountTrend.length - 1].value : tableData.row_count || 0;
        rowCountTrend.push({ timestamp: date.toISOString(), value: lastValue });
      }
      
      nullPercentTrend.push({ timestamp: date.toISOString(), value: avgNullPercent });
    }

    // Get last profiled date
    const lastProfiledRun = tableRuns.sort((a, b) => 
      new Date(b.profiled_at).getTime() - new Date(a.profiled_at).getTime()
    )[0];

    return {
      table_name: tableName,
      schema_name: schema || tableData.schema_name,
      warehouse_type: warehouse || tableData.warehouse_type,
      last_profiled: lastProfiledRun?.profiled_at || tableData.last_profiled,
      row_count: tableData.row_count || 0,
      column_count: tableData.column_count || columns.length,
      total_runs: tableRuns.length,
      drift_count: tableDriftEvents.length,
      row_count_trend: rowCountTrend,
      null_percent_trend: nullPercentTrend,
      columns,
    };
  }

  /**
   * Get table drift history
   */
  async getTableDriftHistory(tableName: string, schema?: string, warehouse?: string, limit?: number): Promise<any[]> {
    let filtered = this.driftEvents.filter(e => 
      e.table_name === tableName &&
      (!schema || e.schema_name === schema) &&
      (!warehouse || e.warehouse_type === warehouse)
    );

    // Sort by timestamp descending
    filtered.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

    return filtered.slice(0, limit || 100);
  }

  /**
   * Compare runs
   */
  async compareRuns(runIds: string[]): Promise<any> {
    const runs = this.runs.filter(r => runIds.includes(r.run_id));
    return {
      runs,
      comparison: {}, // Can be enhanced with detailed comparison
    };
  }

  /**
   * Get run details
   */
  async getRunDetails(runId: string): Promise<any> {
    const run = this.runs.find(r => r.run_id === runId);
    if (!run) {
      return null;
    }

    // Get metrics for this run
    const columns = this.metrics
      .filter(m => m.run_id === runId)
      .map(m => ({
        column_name: m.column_name,
        column_type: m.column_type,
        null_count: m.null_count,
        null_percent: m.null_percent,
        distinct_count: m.distinct_count,
        distinct_percent: m.distinct_percent,
        min_value: m.min_value,
        max_value: m.max_value,
        mean: m.mean,
        stddev: m.stddev,
        histogram: m.histogram,
      }));

    return {
      ...run,
      columns,
    };
  }

  /**
   * Export runs
   */
  async exportRuns(filters: FilterOptions): Promise<any[]> {
    return this.getRuns(filters);
  }

  /**
   * Export drift
   */
  async exportDrift(filters: FilterOptions): Promise<any[]> {
    return this.getDriftAlerts(filters);
  }

  /**
   * Get drift summary
   */
  async getDriftSummary(filters: { warehouse?: string; days?: number }): Promise<any> {
    let filtered = [...this.driftEvents];

    if (filters.warehouse) {
      filtered = filtered.filter(e => e.warehouse_type === filters.warehouse);
    }

    if (filters.days) {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - filters.days);
      filtered = filtered.filter(e => new Date(e.timestamp) >= cutoffDate);
    }

    // Count by severity
    const bySeverity: Record<string, number> = {};
    filtered.forEach(e => {
      const severity = e.severity || e.drift_severity || 'unknown';
      bySeverity[severity] = (bySeverity[severity] || 0) + 1;
    });

    // Count by warehouse
    const byWarehouse: Record<string, number> = {};
    filtered.forEach(e => {
      const wh = e.warehouse_type || 'unknown';
      byWarehouse[wh] = (byWarehouse[wh] || 0) + 1;
    });

    return {
      total: filtered.length,
      by_severity: bySeverity,
      by_warehouse: byWarehouse,
      high_severity_count: bySeverity.high || bySeverity['high'] || 0,
      medium_severity_count: bySeverity.medium || bySeverity['medium'] || 0,
      low_severity_count: bySeverity.low || bySeverity['low'] || 0,
    };
  }

  /**
   * Get drift details
   */
  async getDriftDetails(eventId: string): Promise<any> {
    const event = this.driftEvents.find(e => e.event_id === eventId);
    if (!event) {
      return null;
    }

    // Find the associated run
    const run = this.runs.find(r => r.run_id === event.run_id);

    return {
      ...event,
      run,
    };
  }
}

// Singleton instance
let serviceInstance: DemoDataService | null = null;

/**
 * Get the singleton DemoDataService instance
 */
export function getDemoDataService(): DemoDataService {
  if (!serviceInstance) {
    serviceInstance = new DemoDataService();
  }
  return serviceInstance;
}

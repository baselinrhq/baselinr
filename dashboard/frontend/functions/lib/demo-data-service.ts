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
  public tableQualityScores: any[] = [];
  public columnQualityScores: any[] = [];
  public lineage: any = null;

  /**
   * Load demo data from JSON files
   */
  async loadData(baseUrl: string): Promise<void> {
    // If already loaded, check if data is actually present
    // (in case of previous failed load that set dataLoaded=true with empty arrays)
    if (this.dataLoaded) {
      // If critical data arrays are empty, force a reload
      if (this.runs.length === 0 && this.tables.length === 0) {
        console.warn('[WARNING] dataLoaded=true but arrays are empty, forcing reload');
        this.dataLoaded = false;
        this.loadPromise = null;
      } else {
        return;
      }
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

      // Validate that baseUrl is a valid URL (but keep it as a string for fetching)
      try {
        // Log for debugging
        console.log('[DEBUG] Validating baseUrl:', {
          baseUrl,
          baseUrlType: typeof baseUrl,
          baseUrlLength: baseUrl.length,
        });
        // Validate by creating a URL object (but we'll use the string for fetching)
        new URL(baseUrl);
      } catch (urlError) {
        const errorMsg = urlError instanceof Error ? urlError.message : String(urlError);
        const errorName = urlError instanceof Error ? urlError.name : 'Unknown';
        // Create detailed error message
        const detailedError = `URL_CONSTRUCTOR_FAILED: baseUrl="${baseUrl}", type=${typeof baseUrl}, length=${baseUrl.length}, error="${errorName}: ${errorMsg}"`;
        console.error('[ERROR]', detailedError);
        throw new Error(detailedError);
      }

      // Helper function to fetch JSON files
      // In Cloudflare Pages, we need to fetch from the same origin
      // Use string concatenation like the test endpoint (which works)
      const fetchJson = async (path: string, defaultValue: any = []) => {
        try {
          // Use string concatenation - baseUrl is already a string like "https://example.com/demo_data"
          // Ensure baseUrl doesn't end with / and path doesn't start with /
          const cleanBaseUrl = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
          const cleanPath = path.startsWith('/') ? path.substring(1) : path;
          const fullUrl = `${cleanBaseUrl}/${cleanPath}`;
          
          console.log(`[DEBUG] Fetching ${path} from ${fullUrl}`);

          // Try to fetch the file (simplified to match test endpoint)
          const response = await fetch(fullUrl);
          
          console.log(`[DEBUG] Response for ${path}:`, response.status, response.statusText, response.url);
          
          if (!response.ok) {
            // If we get 404, the file might not be accessible as static asset
            // This is expected in Cloudflare Pages if routing isn't configured correctly
            console.error(`[ERROR] Failed to fetch ${fullUrl}: ${response.status} ${response.statusText}`);
            console.error(`[ERROR] Note: Static files may not be accessible. Consider using /api/demo/data endpoint instead.`);
            // Consume the response body to avoid stalled HTTP response warning
            await response.text().catch(() => {});
            return defaultValue;
          }
          
          const contentType = response.headers.get('content-type');
          console.log(`[DEBUG] Content-Type for ${path}:`, contentType);
          
          const data = await response.json();
          const dataLength = Array.isArray(data) ? data.length : (typeof data === 'object' && data !== null ? Object.keys(data).length : 'scalar');
          const sampleSize = Array.isArray(data) && data.length > 0 ? JSON.stringify(data[0]).substring(0, 100) : (typeof data === 'object' && data !== null ? Object.keys(data).slice(0, 5).join(', ') : String(data).substring(0, 100));
          console.log(`[DEBUG] Loaded ${path}: type=${Array.isArray(data) ? 'array' : typeof data}, length=${dataLength}, sample=${sampleSize}`);
          
          // Warn if we got an empty array when we expected data
          if (Array.isArray(data) && data.length === 0 && defaultValue !== null) {
            console.warn(`[WARNING] ${path} returned empty array (expected non-empty)`);
          }
          
          return data;
        } catch (error) {
          console.error(`Error fetching ${path} from ${baseUrl}/${path}:`, error);
          return defaultValue;
        }
      };

      // Load all JSON files in parallel
      const [runsData, metricsData, driftData, tablesData, validationData, metadataData, tableQualityScoresData, columnQualityScoresData, lineageData] = await Promise.all([
        fetchJson('runs.json', []),
        fetchJson('metrics.json', []),
        fetchJson('drift_events.json', []),
        fetchJson('tables.json', []),
        fetchJson('validation_results.json', []),
        fetchJson('metadata.json', null),
        fetchJson('table_quality_scores.json', []),
        fetchJson('column_quality_scores.json', []),
        fetchJson('lineage.json', null),
      ]);

      this.runs = Array.isArray(runsData) ? runsData : [];
      this.metrics = Array.isArray(metricsData) ? metricsData : [];
      this.driftEvents = Array.isArray(driftData) ? driftData : [];
      this.tables = Array.isArray(tablesData) ? tablesData : [];
      this.validationResults = Array.isArray(validationData) ? validationData : [];
      this.metadataData = metadataData;
      this.tableQualityScores = Array.isArray(tableQualityScoresData) ? tableQualityScoresData : [];
      this.columnQualityScores = Array.isArray(columnQualityScoresData) ? columnQualityScoresData : [];
      this.lineage = lineageData;
      
      console.log(`[DEBUG] Data loaded: ${this.runs.length} runs, ${this.metrics.length} metrics, ${this.driftEvents.length} drift events, ${this.tables.length} tables, ${this.validationResults.length} validations, ${this.tableQualityScores.length} table quality scores, ${this.columnQualityScores.length} column quality scores, lineage: ${this.lineage ? 'loaded' : 'none'}`);
      
      // Warn if critical data arrays are empty (shouldn't happen if files are accessible)
      if (this.runs.length === 0 && this.tables.length === 0) {
        console.warn('[WARNING] Critical data arrays (runs, tables) are empty after load. Files may not be accessible or may be empty.');
      }
      
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
      this.tableQualityScores = [];
      this.columnQualityScores = [];
      this.lineage = null;
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
    let filtered = [...this.validationResults];

    // Apply filters
    if (filters.warehouse) {
      filtered = filtered.filter(v => v.warehouse_type === filters.warehouse);
    }

    if (filters.days) {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - filters.days);
      filtered = filtered.filter(v => {
        const validatedDate = v.validated_at || v.timestamp;
        return validatedDate && new Date(validatedDate) >= cutoffDate;
      });
    }

    const total = filtered.length;
    const passed = filtered.filter(v => v.passed === true || v.status === 'pass').length;
    const failed = filtered.filter(v => v.passed === false || v.status === 'fail').length;
    const passRate = total > 0 ? (passed / total) * 100 : 0;

    // Count by rule type
    const byRuleType: Record<string, number> = {};
    filtered.forEach(v => {
      const ruleType = v.rule_type || 'unknown';
      byRuleType[ruleType] = (byRuleType[ruleType] || 0) + 1;
    });

    // Count by severity
    const bySeverity: Record<string, number> = { low: 0, medium: 0, high: 0 };
    filtered.forEach(v => {
      const severity = (v.severity || 'low').toLowerCase();
      if (severity === 'low' || severity === 'medium' || severity === 'high') {
        bySeverity[severity] = (bySeverity[severity] || 0) + 1;
      }
    });

    // Count by table
    const byTable: Record<string, number> = {};
    filtered.forEach(v => {
      const table = v.table_name || 'unknown';
      byTable[table] = (byTable[table] || 0) + 1;
    });

    // Generate trending data (pass rate over time)
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - (filters.days || 30));
    const trending: Array<{ timestamp: string; value: number }> = [];
    for (let i = 0; i < (filters.days || 30); i++) {
      const date = new Date(thirtyDaysAgo);
      date.setDate(date.getDate() + i);
      const dateStr = date.toISOString().split('T')[0];
      const dayValidations = filtered.filter(v => {
        const validatedDate = v.validated_at || v.timestamp;
        if (!validatedDate) return false;
        return new Date(validatedDate).toISOString().split('T')[0] === dateStr;
      });
      if (dayValidations.length > 0) {
        const dayPassed = dayValidations.filter(v => v.passed === true || v.status === 'pass').length;
        const dayPassRate = (dayPassed / dayValidations.length) * 100;
        trending.push({ timestamp: date.toISOString(), value: dayPassRate });
      } else {
        // Include days with no data as well, using previous day's rate or 100
        const prevValue = trending.length > 0 ? trending[trending.length - 1].value : 100;
        trending.push({ timestamp: date.toISOString(), value: prevValue });
      }
    }

    // Get recent validation runs (group by run_id)
    const runsMap = new Map<string, any>();
    filtered.forEach(v => {
      const runId = v.run_id || 'unknown';
      if (!runsMap.has(runId)) {
        runsMap.set(runId, {
          run_id: runId,
          validated_at: v.validated_at || v.timestamp || new Date().toISOString(),
          total: 0,
          passed: 0,
          failed: 0,
        });
      }
      const run = runsMap.get(runId);
      run.total++;
      if (v.passed === true || v.status === 'pass') {
        run.passed++;
      } else {
        run.failed++;
      }
    });
    const recentRuns = Array.from(runsMap.values())
      .sort((a, b) => new Date(b.validated_at).getTime() - new Date(a.validated_at).getTime())
      .slice(0, 10);

    return {
      total_validations: total,
      passed_count: passed,
      failed_count: failed,
      pass_rate: passRate,
      by_rule_type: byRuleType,
      by_severity: bySeverity,
      by_table: byTable,
      trending,
      recent_runs: recentRuns,
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

    const days = filters.days || 30;
    if (days) {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - days);
      filtered = filtered.filter(e => {
        const eventDate = e.timestamp || e.detected_at;
        return eventDate && new Date(eventDate) >= cutoffDate;
      });
    }

    // Count by severity (structured as {low, medium, high})
    const bySeverity = { low: 0, medium: 0, high: 0 };
    filtered.forEach(e => {
      const severity = ((e.severity || e.drift_severity || 'low') as string).toLowerCase();
      if (severity === 'low' || severity === 'medium' || severity === 'high') {
        bySeverity[severity as 'low' | 'medium' | 'high']++;
      }
    });

    // Count by warehouse
    const warehouseBreakdown: Record<string, number> = {};
    filtered.forEach(e => {
      const wh = e.warehouse_type || 'unknown';
      warehouseBreakdown[wh] = (warehouseBreakdown[wh] || 0) + 1;
    });

    // Generate trending data (event count over time)
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - days);
    const trending: Array<{ timestamp: string; value: number }> = [];
    for (let i = 0; i < days; i++) {
      const date = new Date(thirtyDaysAgo);
      date.setDate(date.getDate() + i);
      const dateStr = date.toISOString().split('T')[0];
      const count = filtered.filter(e => {
        const eventDate = e.timestamp || e.detected_at;
        if (!eventDate) return false;
        return new Date(eventDate).toISOString().split('T')[0] === dateStr;
      }).length;
      trending.push({ timestamp: date.toISOString(), value: count });
    }

    // Top affected tables (with severity breakdown per table)
    const tableMap = new Map<string, { low: number; medium: number; high: number; total: number }>();
    filtered.forEach(e => {
      const tableName = e.table_name || 'unknown';
      if (!tableMap.has(tableName)) {
        tableMap.set(tableName, { low: 0, medium: 0, high: 0, total: 0 });
      }
      const tableData = tableMap.get(tableName)!;
      tableData.total++;
      const severity = ((e.severity || e.drift_severity || 'low') as string).toLowerCase();
      if (severity === 'low' || severity === 'medium' || severity === 'high') {
        tableData[severity as 'low' | 'medium' | 'high']++;
      }
    });

    const topAffectedTables = Array.from(tableMap.entries())
      .map(([table_name, counts]) => ({
        table_name,
        drift_count: counts.total,
        severity_breakdown: {
          low: counts.low,
          medium: counts.medium,
          high: counts.high,
        },
      }))
      .sort((a, b) => b.drift_count - a.drift_count)
      .slice(0, 10);

    // Recent activity (most recent drift events)
    const recentActivity = filtered
      .sort((a, b) => {
        const aTime = new Date(a.timestamp || a.detected_at || 0).getTime();
        const bTime = new Date(b.timestamp || b.detected_at || 0).getTime();
        return bTime - aTime;
      })
      .slice(0, 10)
      .map(e => ({
        event_id: e.event_id || e.alert_id || '',
        run_id: e.run_id || '',
        table_name: e.table_name || '',
        column_name: e.column_name || null,
        metric_name: e.metric_name || '',
        baseline_value: e.baseline_value || null,
        current_value: e.current_value || null,
        change_percent: e.change_percent || e.change_percentage || null,
        severity: (e.severity || e.drift_severity || 'low') as 'low' | 'medium' | 'high',
        timestamp: e.timestamp || e.detected_at || new Date().toISOString(),
        detected_at: e.detected_at || e.timestamp,
        warehouse_type: e.warehouse_type || '',
        warehouse: e.warehouse || e.warehouse_type,
        schema: e.schema || e.schema_name,
      }));

    return {
      total_events: filtered.length,
      by_severity: bySeverity,
      trending,
      top_affected_tables: topAffectedTables,
      warehouse_breakdown: warehouseBreakdown,
      recent_activity: recentActivity,
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

  /**
   * Get quality scores list
   */
  getQualityScores(filters: { schema?: string; status?: string }): any {
    let scores = this.tableQualityScores;

    // Get latest score for each table
    const latestScoresMap = new Map<string, any>();
    scores.forEach(score => {
      const key = `${score.schema_name || ''}.${score.table_name}`;
      const existing = latestScoresMap.get(key);
      if (!existing || new Date(score.calculated_at) > new Date(existing.calculated_at)) {
        latestScoresMap.set(key, score);
      }
    });

    let filtered = Array.from(latestScoresMap.values());

    if (filters.schema) {
      filtered = filtered.filter(s => s.schema_name === filters.schema);
    }
    if (filters.status) {
      filtered = filtered.filter(s => s.status === filters.status);
    }

    // Transform to match QualityScore type
    return filtered.map(score => ({
      table_name: score.table_name,
      schema_name: score.schema_name,
      overall_score: score.overall_score,
      status: score.status,
      components: {
        completeness: score.completeness_score,
        validity: score.validity_score,
        consistency: score.consistency_score,
        freshness: score.freshness_score,
        uniqueness: score.uniqueness_score,
        accuracy: score.accuracy_score,
      },
      issues: {
        total: score.total_issues || 0,
        critical: score.critical_issues || 0,
        warnings: score.warnings || 0,
      },
      calculated_at: score.calculated_at,
      run_id: score.run_id || null,
    }));
  }

  /**
   * Get quality score for a specific table
   */
  getTableQualityScore(tableName: string, schema?: string): any {
    let scores = this.tableQualityScores.filter(s => s.table_name === tableName);
    if (schema) {
      scores = scores.filter(s => s.schema_name === schema);
    }

    if (scores.length === 0) {
      return null;
    }

    // Get latest score
    const latest = scores.sort((a, b) => 
      new Date(b.calculated_at).getTime() - new Date(a.calculated_at).getTime()
    )[0];

    return {
      table_name: latest.table_name,
      schema_name: latest.schema_name,
      overall_score: latest.overall_score,
      status: latest.status,
      components: {
        completeness: latest.completeness_score,
        validity: latest.validity_score,
        consistency: latest.consistency_score,
        freshness: latest.freshness_score,
        uniqueness: latest.uniqueness_score,
        accuracy: latest.accuracy_score,
      },
      issues: {
        total: latest.total_issues || 0,
        critical: latest.critical_issues || 0,
        warnings: latest.warnings || 0,
      },
      calculated_at: latest.calculated_at,
      run_id: latest.run_id || null,
    };
  }

  /**
   * Get quality score history for a table
   */
  getTableQualityScoreHistory(tableName: string, schema?: string, days?: number): any[] {
    let scores = this.tableQualityScores.filter(s => s.table_name === tableName);
    if (schema) {
      scores = scores.filter(s => s.schema_name === schema);
    }

    // Filter by date if days specified
    if (days) {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - days);
      scores = scores.filter(s => new Date(s.calculated_at) >= cutoffDate);
    }

    // Sort by date descending
    scores.sort((a, b) => new Date(b.calculated_at).getTime() - new Date(a.calculated_at).getTime());

    return scores.map(score => ({
      table_name: score.table_name,
      schema_name: score.schema_name,
      overall_score: score.overall_score,
      status: score.status,
      components: {
        completeness: score.completeness_score,
        validity: score.validity_score,
        consistency: score.consistency_score,
        freshness: score.freshness_score,
        uniqueness: score.uniqueness_score,
        accuracy: score.accuracy_score,
      },
      issues: {
        total: score.total_issues || 0,
        critical: score.critical_issues || 0,
        warnings: score.warnings || 0,
      },
      calculated_at: score.calculated_at,
      run_id: score.run_id || null,
    }));
  }

  /**
   * Get system quality score
   */
  getSystemQualityScore(): any {
    // Get latest score for each table
    const latestScoresMap = new Map<string, any>();
    this.tableQualityScores.forEach(score => {
      const key = `${score.schema_name || ''}.${score.table_name}`;
      const existing = latestScoresMap.get(key);
      if (!existing || new Date(score.calculated_at) > new Date(existing.calculated_at)) {
        latestScoresMap.set(key, score);
      }
    });

    const scores = Array.from(latestScoresMap.values());
    if (scores.length === 0) {
      return {
        overall_score: 85,
        status: 'healthy',
        total_tables: 0,
        healthy_count: 0,
        warning_count: 0,
        critical_count: 0,
      };
    }

    const avgScore = scores.reduce((sum, s) => sum + s.overall_score, 0) / scores.length;
    const healthy = scores.filter(s => s.status === 'healthy').length;
    const warning = scores.filter(s => s.status === 'warning').length;
    const critical = scores.filter(s => s.status === 'critical').length;

    return {
      overall_score: Math.round(avgScore * 100) / 100,
      status: avgScore >= 80 ? 'healthy' : avgScore >= 60 ? 'warning' : 'critical',
      total_tables: scores.length,
      healthy_count: healthy,
      warning_count: warning,
      critical_count: critical,
    };
  }

  /**
   * Get column quality scores for a table
   */
  getColumnQualityScores(tableName: string, schema?: string, days?: number): any[] {
    let scores = this.columnQualityScores.filter(s => s.table_name === tableName);
    if (schema) {
      scores = scores.filter(s => s.schema_name === schema);
    }

    if (days) {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - days);
      scores = scores.filter(s => new Date(s.calculated_at) >= cutoffDate);
    }

    // Get latest score for each column
    const latestScoresMap = new Map<string, any>();
    scores.forEach(score => {
      const key = score.column_name;
      const existing = latestScoresMap.get(key);
      if (!existing || new Date(score.calculated_at) > new Date(existing.calculated_at)) {
        latestScoresMap.set(key, score);
      }
    });

    return Array.from(latestScoresMap.values()).map(score => ({
      table_name: score.table_name,
      schema_name: score.schema_name,
      column_name: score.column_name,
      overall_score: score.overall_score,
      status: score.status,
      components: {
        completeness: score.completeness_score,
        validity: score.validity_score,
        consistency: score.consistency_score,
        freshness: score.freshness_score || 0,
        uniqueness: score.uniqueness_score,
        accuracy: score.accuracy_score || 0,
      },
      calculated_at: score.calculated_at,
      run_id: score.run_id || null,
      period_start: score.period_start,
      period_end: score.period_end,
    }));
  }

  /**
   * Generate RCA list items from drift events and validation failures
   */
  getRCAListItems(filters: FilterOptions): any[] {
    const rcaItems: any[] = [];
    
    // Generate RCA items from high/medium severity drift events
    const driftEvents = this.driftEvents.filter(e => {
      const severity = (e.severity || e.drift_severity || 'low').toLowerCase();
      return severity === 'high' || severity === 'medium';
    });

    // Create RCA items from drift events
    driftEvents.slice(0, 20).forEach((event, index) => {
      const anomalyId = `rca-${event.event_id || `drift-${index}`}`;
      const severity = (event.severity || event.drift_severity || 'medium').toLowerCase();
      const rcaStatus = index % 3 === 0 ? 'analyzed' : index % 3 === 1 ? 'pending' : 'dismissed';
      
      const numCauses = rcaStatus === 'analyzed' ? Math.floor(Math.random() * 3) + 2 : 0;
      const topCause = numCauses > 0 ? {
        cause_type: ['Data Pipeline', 'Schema Change', 'Data Quality', 'External System'][index % 4],
        confidence_score: 0.6 + (Math.random() * 0.3),
        description: 'Detected significant change in data patterns',
      } : null;

      rcaItems.push({
        anomaly_id: anomalyId,
        table_name: event.table_name || '',
        schema_name: event.schema_name || null,
        column_name: event.column_name || null,
        metric_name: event.metric_name || null,
        analyzed_at: event.timestamp || event.detected_at || new Date().toISOString(),
        rca_status: rcaStatus,
        num_causes: numCauses,
        top_cause: topCause,
      });
    });

    // Apply filters
    let filtered = rcaItems;
    if (filters.status) {
      filtered = filtered.filter(item => item.rca_status === filters.status);
    }
    if (filters.table) {
      filtered = filtered.filter(item => item.table_name === filters.table);
    }
    if (filters.schema) {
      filtered = filtered.filter(item => item.schema_name === filters.schema);
    }

    // Sort by analyzed_at descending
    filtered.sort((a, b) => new Date(b.analyzed_at).getTime() - new Date(a.analyzed_at).getTime());

    return filtered;
  }

  /**
   * Get RCA statistics
   */
  getRCAStatistics(): any {
    const allItems = this.getRCAListItems({});
    const total = allItems.length;
    const analyzed = allItems.filter(item => item.rca_status === 'analyzed').length;
    const pending = allItems.filter(item => item.rca_status === 'pending').length;
    const dismissed = allItems.filter(item => item.rca_status === 'dismissed').length;
    
    const analyzedItems = allItems.filter(item => item.rca_status === 'analyzed');
    const totalCauses = analyzedItems.reduce((sum, item) => sum + (item.num_causes || 0), 0);
    const avgCauses = analyzedItems.length > 0 ? totalCauses / analyzedItems.length : 0;

    return {
      total_analyses: total,
      analyzed,
      dismissed,
      pending,
      avg_causes_per_anomaly: avgCauses,
    };
  }

  /**
   * Generate recommendations from tables
   */
  getRecommendations(options: { schema?: string; include_columns?: boolean }): any {
    // Get unique tables (may have duplicates across runs)
    const tableMap = new Map<string, any>();
    this.tables.forEach(table => {
      const key = `${table.schema_name || 'public'}.${table.table_name}`;
      if (!tableMap.has(key)) {
        tableMap.set(key, table);
      }
    });

    let filteredTables = Array.from(tableMap.values());
    if (options.schema) {
      filteredTables = filteredTables.filter(t => t.schema_name === options.schema);
    }

    // Sort by table name for consistency
    filteredTables.sort((a, b) => {
      const aName = `${a.schema_name || 'public'}.${a.table_name}`;
      const bName = `${b.schema_name || 'public'}.${b.table_name}`;
      return aName.localeCompare(bName);
    });

    // Generate recommendations for top tables (limit to 15 for demo)
    const recommendedTables = filteredTables.slice(0, 15).map((table, index) => {
      const schema = table.schema_name || 'public';
      const tableName = table.table_name;
      
      // Calculate confidence based on row count and other factors
      const rowCount = table.row_count || 0;
      const hasData = rowCount > 0;
      const confidence = hasData 
        ? Math.min(0.95, 0.6 + (rowCount / 1000000) * 0.3 + Math.random() * 0.1)
        : 0.4 + Math.random() * 0.2;

      // Generate reasons
      const reasons: string[] = [];
      if (rowCount > 100000) {
        reasons.push(`Large table with ${rowCount.toLocaleString()} rows`);
      } else if (rowCount > 10000) {
        reasons.push(`Table with ${rowCount.toLocaleString()} rows`);
      } else {
        reasons.push(`Table with ${rowCount.toLocaleString()} rows`);
      }
      
      // Check if table appears in runs frequently
      const runCount = this.runs.filter(r => r.dataset_name === tableName && r.schema_name === schema).length;
      if (runCount > 5) {
        reasons.push(`Profiled ${runCount} times in recent runs`);
      }
      
      // Check for drift events
      const driftCount = this.driftEvents.filter(e => e.table_name === tableName && e.schema_name === schema).length;
      if (driftCount > 0) {
        reasons.push(`Has ${driftCount} drift event${driftCount > 1 ? 's' : ''} detected`);
      }

      // Generate column recommendations if requested
      const columnRecommendations: any[] = [];
      if (options.include_columns && table.columns && Array.isArray(table.columns)) {
        // Get column quality scores for this table
        const tableColumns = table.columns.slice(0, 10); // Limit to 10 columns
        tableColumns.forEach((col: any, colIndex: number) => {
          const colName = col.column_name || col.name || `column_${colIndex}`;
          const colType = col.data_type || col.type || 'unknown';
          
          // Generate suggested checks based on column type and name
          const suggestedChecks: any[] = [];
          const signals: string[] = [];
          
          // ID columns
          if (colName.toLowerCase().endsWith('_id') || colName.toLowerCase() === 'id') {
            signals.push('Column name matches pattern: *_id');
            suggestedChecks.push({
              type: 'uniqueness',
              confidence: 0.95,
              config: { threshold: 1.0 },
            });
            suggestedChecks.push({
              type: 'completeness',
              confidence: 0.90,
              config: { min_completeness: 1.0 },
            });
          }
          
          // Timestamp columns
          if (colType.toLowerCase().includes('timestamp') || 
              colType.toLowerCase().includes('date') ||
              colName.toLowerCase().includes('_at') ||
              colName.toLowerCase().includes('date')) {
            signals.push('Timestamp/date column detected');
            suggestedChecks.push({
              type: 'freshness',
              confidence: 0.90,
              config: { max_age_hours: 24 },
            });
            suggestedChecks.push({
              type: 'completeness',
              confidence: 0.85,
              config: { min_completeness: 0.95 },
            });
          }
          
          // Email columns
          if (colName.toLowerCase().includes('email')) {
            signals.push('Email pattern match in column name');
            suggestedChecks.push({
              type: 'format_email',
              confidence: 0.92,
              config: { pattern: 'email' },
            });
          }
          
          // Default completeness check for all columns
          if (suggestedChecks.length === 0) {
            signals.push('Standard column recommendation');
            suggestedChecks.push({
              type: 'completeness',
              confidence: 0.75,
              config: { min_completeness: 0.90 },
            });
          }

          if (suggestedChecks.length > 0) {
            columnRecommendations.push({
              column: colName,
              data_type: colType,
              confidence: Math.min(0.95, 0.7 + Math.random() * 0.25),
              signals,
              suggested_checks: suggestedChecks,
            });
          }
        });
      }

      return {
        schema,
        table: tableName,
        database: table.database_name || null,
        confidence: Math.round(confidence * 100) / 100,
        score: Math.round((confidence * 100) * 100) / 100,
        reasons: reasons.length > 0 ? reasons : ['Recommended for monitoring'],
        warnings: rowCount === 0 ? ['Table appears to be empty'] : [],
        suggested_checks: ['completeness', 'validity', 'freshness'],
        column_recommendations: columnRecommendations,
        low_confidence_columns: [],
        query_count: runCount,
        queries_per_day: runCount > 0 ? runCount / 30 : 0,
        row_count: rowCount,
        last_query_days_ago: runCount > 0 ? Math.floor(Math.random() * 7) : null,
        column_count: table.columns ? (Array.isArray(table.columns) ? table.columns.length : 0) : 0,
        lineage_score: driftCount > 0 ? 0.8 : 0.5,
        lineage_context: driftCount > 0 ? { has_drift_events: true, event_count: driftCount } : null,
      };
    });

    // Excluded tables (tables with very low row counts or no data)
    const excludedTables = filteredTables.slice(15).filter(table => {
      const rowCount = table.row_count || 0;
      return rowCount < 100;
    }).slice(0, 5).map(table => ({
      schema: table.schema_name || 'public',
      table: table.table_name,
      database: table.database_name || null,
      reasons: ['Low row count or insufficient data'],
    }));

    // Calculate statistics
    const totalColumnsAnalyzed = recommendedTables.reduce((sum, t) => sum + (t.column_count || 0), 0);
    const totalColumnChecksRecommended = recommendedTables.reduce((sum, t) => 
      sum + (t.column_recommendations?.length || 0), 0
    , 0);

    return {
      generated_at: new Date().toISOString(),
      lookback_days: 30,
      database_type: 'postgres',
      recommended_tables: recommendedTables,
      excluded_tables: excludedTables,
      total_tables_analyzed: filteredTables.length,
      total_recommended: recommendedTables.length,
      total_excluded: excludedTables.length,
      confidence_distribution: {
        high: recommendedTables.filter(t => t.confidence >= 0.8).length,
        medium: recommendedTables.filter(t => t.confidence >= 0.5 && t.confidence < 0.8).length,
        low: recommendedTables.filter(t => t.confidence < 0.5).length,
      },
      total_columns_analyzed: totalColumnsAnalyzed,
      total_column_checks_recommended: totalColumnChecksRecommended,
      column_confidence_distribution: {
        high: recommendedTables.reduce((sum, t) => 
          sum + (t.column_recommendations?.filter((c: any) => c.confidence >= 0.8).length || 0), 0
        ),
        medium: recommendedTables.reduce((sum, t) => 
          sum + (t.column_recommendations?.filter((c: any) => c.confidence >= 0.5 && c.confidence < 0.8).length || 0), 0
        ),
        low: recommendedTables.reduce((sum, t) => 
          sum + (t.column_recommendations?.filter((c: any) => c.confidence < 0.5).length || 0), 0
        ),
      },
      low_confidence_suggestions: [],
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

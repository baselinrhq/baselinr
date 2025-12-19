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
      // Load all JSON files in parallel
      const [runsData, metricsData, driftData, tablesData, validationData, metadataData] = await Promise.all([
        fetch(`${baseUrl}/runs.json`).then(r => r.json()).catch(() => []),
        fetch(`${baseUrl}/metrics.json`).then(r => r.json()).catch(() => []),
        fetch(`${baseUrl}/drift_events.json`).then(r => r.json()).catch(() => []),
        fetch(`${baseUrl}/tables.json`).then(r => r.json()).catch(() => []),
        fetch(`${baseUrl}/validation_results.json`).then(r => r.json()).catch(() => []),
        fetch(`${baseUrl}/metadata.json`).then(r => r.json()).catch(() => null),
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
      filtered = filtered.filter(d => d.drift_severity === filters.severity);
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
    return {
      total_validations: this.validationResults.length,
      passed: this.validationResults.filter(v => v.status === 'pass').length,
      failed: this.validationResults.filter(v => v.status === 'fail').length,
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

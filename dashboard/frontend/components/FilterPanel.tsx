interface FilterPanelProps {
  filters: Record<string, string>
  onChange: (filters: Record<string, string>) => void
  type?: 'runs' | 'drift'
}

export default function FilterPanel({ filters, onChange, type = 'runs' }: FilterPanelProps) {
  const handleChange = (key: string, value: string) => {
    onChange({ ...filters, [key]: value })
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Filters</h3>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Warehouse
          </label>
          <select
            value={filters.warehouse || ''}
            onChange={(e) => handleChange('warehouse', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Warehouses</option>
            <option value="postgres">PostgreSQL</option>
            <option value="snowflake">Snowflake</option>
            <option value="mysql">MySQL</option>
            <option value="bigquery">BigQuery</option>
            <option value="redshift">Redshift</option>
            <option value="sqlite">SQLite</option>
          </select>
        </div>

        {type === 'runs' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Schema
            </label>
            <input
              type="text"
              value={filters.schema || ''}
              onChange={(e) => handleChange('schema', e.target.value)}
              placeholder="Enter schema name"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Table
          </label>
          <input
            type="text"
            value={filters.table || ''}
            onChange={(e) => handleChange('table', e.target.value)}
            placeholder="Enter table name"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {type === 'runs' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Status
            </label>
            <select
              value={filters.status || ''}
              onChange={(e) => handleChange('status', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All Statuses</option>
              <option value="success">Success</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        )}

        {type === 'drift' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Severity
            </label>
            <select
              value={filters.severity || ''}
              onChange={(e) => handleChange('severity', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All Severities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Time Range
          </label>
          <select
            value={filters.days || 30}
            onChange={(e) => handleChange('days', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="365">Last year</option>
          </select>
        </div>
      </div>

      <div className="mt-4 flex justify-end gap-2">
        <button
          onClick={() => onChange({ warehouse: '', schema: '', table: '', status: '', severity: '', days: '30' })}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Clear Filters
        </button>
      </div>
    </div>
  )
}


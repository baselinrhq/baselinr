'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FormField } from '@/components/ui/FormField'
import { Select, SelectOption } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { discoverTables, getTablePreview, TableMetadataResponse, TableInfo } from '@/lib/api/tables'
import { ValidationRuleConfig } from '@/types/config'

export interface ReferentialRuleFormProps {
  rule: ValidationRuleConfig
  onChange: (rule: ValidationRuleConfig) => void
  errors?: Record<string, string>
  connectionId?: string
}

export function ReferentialRuleForm({ rule, onChange, errors, connectionId }: ReferentialRuleFormProps) {
  const [referenceSchema, setReferenceSchema] = useState<string>(
    rule.references?.schema || 'public'
  )
  const [referenceTable, setReferenceTable] = useState<string>(
    rule.references?.table || ''
  )
  const [referenceColumn, setReferenceColumn] = useState<string>(
    rule.references?.column || ''
  )

  // Fetch tables for reference table selector
  const { data: tablesData, isLoading: isLoadingTables } = useQuery<{ tables: TableInfo[] }>({
    queryKey: ['tables', 'discover', referenceSchema, connectionId],
    queryFn: async () => {
      const result = await discoverTables(
        {
          schemas: [referenceSchema],
        },
        connectionId
      )
      return { tables: result.tables }
    },
    enabled: !!referenceSchema,
  })

  // Fetch columns for reference column selector
  const { data: tableMetadata, isLoading: isLoadingColumns } = useQuery<TableMetadataResponse>({
    queryKey: ['table', 'preview', referenceSchema, referenceTable, connectionId],
    queryFn: () => getTablePreview(referenceSchema, referenceTable, connectionId),
    enabled: !!referenceSchema && !!referenceTable,
  })

  // Update rule when reference changes
  useEffect(() => {
    if (referenceTable && referenceColumn) {
      onChange({
        ...rule,
        references: {
          table: referenceTable,
          column: referenceColumn,
          ...(referenceSchema !== 'public' && { schema: referenceSchema }),
        },
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [referenceSchema, referenceTable, referenceColumn])

  const tableOptions: SelectOption[] = (tablesData?.tables || []).map((table) => ({
    value: table.table,
    label: `${table.schema}.${table.table}`,
  }))

  const columnOptions: SelectOption[] = (tableMetadata?.columns || []).map((col) => ({
    value: col.name,
    label: `${col.name} (${col.type})`,
  }))

  return (
    <div className="space-y-4">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-medium text-blue-900 mb-2">Reference Configuration</h4>
        <p className="text-sm text-blue-700">
          This rule validates that values in <strong>{rule.table}.{rule.column}</strong> exist in
          the referenced table and column.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <FormField
          label="Reference Schema"
          error={errors?.references}
          required
        >
          <Input
            value={referenceSchema}
            onChange={(e) => setReferenceSchema(e.target.value)}
            placeholder="public"
          />
        </FormField>

        <FormField
          label="Reference Table"
          error={errors?.references}
          required
        >
          {isLoadingTables ? (
            <LoadingSpinner size="sm" />
          ) : (
            <Select
              value={referenceTable}
              onChange={(value) => {
                setReferenceTable(value)
                setReferenceColumn('') // Reset column when table changes
              }}
              options={tableOptions}
              placeholder="Select table"
            />
          )}
        </FormField>
      </div>

      <FormField
        label="Reference Column"
        error={errors?.references}
        required
        helperText="Column in the referenced table that should match"
      >
        {isLoadingColumns ? (
          <LoadingSpinner size="sm" />
        ) : (
          <Select
            value={referenceColumn}
            onChange={setReferenceColumn}
            options={columnOptions}
            placeholder="Select column"
            disabled={!referenceTable}
          />
        )}
      </FormField>

      {referenceTable && referenceColumn && (
        <div className="text-sm text-green-600 bg-green-50 p-2 rounded">
          ✓ Reference configured: {referenceSchema}.{referenceTable}.{referenceColumn}
        </div>
      )}

      <div className="text-sm text-gray-600">
        <p className="font-medium mb-1">Note:</p>
        <ul className="list-disc list-inside space-y-1 ml-2">
          <li>Validates foreign key relationships between tables</li>
          <li>Values in the source column must exist in the referenced table column</li>
          <li>Both tables must be accessible from the same connection</li>
        </ul>
      </div>
    </div>
  )
}


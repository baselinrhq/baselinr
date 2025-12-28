'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { 
  FileText, 
  ChevronRight, 
  CheckCircle, 
  AlertCircle,
  RefreshCw,
  ExternalLink,
  Database,
  Shield,
  Users
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { ContractValidationResult } from '@/types/odcs'
import { listContracts, validateContracts } from '@/lib/api/contracts'

export default function ContractsPageClient() {
  const [isValidating, setIsValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<ContractValidationResult | null>(null)

  const { 
    data: contractsData, 
    isLoading, 
    error, 
    refetch 
  } = useQuery({
    queryKey: ['contracts'],
    queryFn: listContracts,
    refetchOnWindowFocus: false,
  })

  const handleValidate = async () => {
    setIsValidating(true)
    try {
      const result = await validateContracts()
      setValidationResult(result)
    } catch (err) {
      console.error('Validation failed:', err)
    } finally {
      setIsValidating(false)
    }
  }

  const contracts = contractsData?.contracts || []

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
            <Link href="/config" className="hover:text-cyan-400">
              Configuration
            </Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-white font-medium">Data Contracts</span>
          </div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText className="w-6 h-6" />
            ODCS Data Contracts
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage Open Data Contract Standard (ODCS) contracts for your datasets
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            onClick={() => refetch()}
            disabled={isLoading}
            icon={<RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />}
          >
            Refresh
          </Button>
          <Button
            onClick={handleValidate}
            disabled={isValidating}
            loading={isValidating}
            icon={<Shield className="w-4 h-4" />}
          >
            Validate All
          </Button>
        </div>
      </div>

      {/* Validation Results */}
      {validationResult && (
        <Card className={validationResult.valid ? 'border-emerald-500/50' : 'border-rose-500/50'}>
          <div className="flex items-start gap-4">
            {validationResult.valid ? (
              <CheckCircle className="w-6 h-6 text-emerald-400 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-6 h-6 text-rose-400 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <h3 className={`font-semibold ${validationResult.valid ? 'text-emerald-400' : 'text-rose-400'}`}>
                {validationResult.valid ? 'All Contracts Valid' : 'Validation Issues Found'}
              </h3>
              <p className="text-sm text-slate-400 mt-1">
                Checked {validationResult.contracts_checked} contract(s)
              </p>
              
              {validationResult.errors.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-rose-400 mb-2">Errors ({validationResult.errors.length})</h4>
                  <ul className="space-y-1">
                    {validationResult.errors.map((error, idx) => (
                      <li key={idx} className="text-sm text-slate-300">
                        <span className="text-slate-500">[{error.contract}]</span> {error.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {validationResult.warnings.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-amber-400 mb-2">Warnings ({validationResult.warnings.length})</h4>
                  <ul className="space-y-1">
                    {validationResult.warnings.slice(0, 5).map((warning, idx) => (
                      <li key={idx} className="text-sm text-slate-300">
                        <span className="text-slate-500">[{warning.contract}]</span> {warning.message}
                      </li>
                    ))}
                    {validationResult.warnings.length > 5 && (
                      <li className="text-sm text-slate-500">
                        ...and {validationResult.warnings.length - 5} more
                      </li>
                    )}
                  </ul>
                </div>
              )}
            </div>
            <button
              onClick={() => setValidationResult(null)}
              className="text-slate-400 hover:text-slate-300"
            >
              ×
            </button>
          </div>
        </Card>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="text-center py-12">
          <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
          <p className="text-slate-400 mt-4">Loading contracts...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <Card className="border-rose-500/50">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-rose-400" />
            <p className="text-rose-400">Failed to load contracts: {error.message}</p>
          </div>
        </Card>
      )}

      {/* Empty State */}
      {!isLoading && !error && contracts.length === 0 && (
        <Card>
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-slate-600 mx-auto" />
            <h3 className="text-lg font-medium text-white mt-4">No Contracts Found</h3>
            <p className="text-slate-400 mt-2 max-w-md mx-auto">
              No ODCS contracts were found in the contracts directory. 
              Create <code className="text-cyan-400">.odcs.yaml</code> files to define your data contracts.
            </p>
            <div className="mt-6">
              <a
                href="https://bitol-io.github.io/open-data-contract-standard/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-cyan-400 hover:text-cyan-300"
              >
                <ExternalLink className="w-4 h-4" />
                Learn about ODCS
              </a>
            </div>
          </div>
        </Card>
      )}

      {/* Contracts List */}
      {!isLoading && !error && contracts.length > 0 && (
        <div className="grid gap-4">
          {contracts.map((contract) => (
            <Link
              key={contract.id || 'unnamed'}
              href={`/config/contracts/${encodeURIComponent(contract.id || 'unnamed')}`}
            >
              <Card className="hover:border-cyan-500/50 transition-colors cursor-pointer">
                <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-lg font-semibold text-white">
                      {contract.title || contract.id || 'Untitled Contract'}
                    </h3>
                    <span className={`
                      px-2 py-0.5 text-xs rounded-full
                      ${contract.status === 'active' 
                        ? 'bg-emerald-500/20 text-emerald-400' 
                        : contract.status === 'draft'
                        ? 'bg-amber-500/20 text-amber-400'
                        : 'bg-slate-500/20 text-slate-400'}
                    `}>
                      {contract.status || 'unknown'}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-4 mt-2 text-sm text-slate-400">
                    {contract.owner && (
                      <span className="flex items-center gap-1">
                        <Users className="w-4 h-4" />
                        {contract.owner}
                      </span>
                    )}
                    {contract.domain && (
                      <span className="px-2 py-0.5 bg-slate-700/50 rounded text-xs">
                        {contract.domain}
                      </span>
                    )}
                  </div>

                  {contract.datasets.length > 0 && (
                    <div className="flex items-center gap-2 mt-3">
                      <Database className="w-4 h-4 text-slate-500" />
                      <span className="text-sm text-slate-300">
                        {contract.datasets.join(', ')}
                      </span>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-6 text-sm">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-cyan-400">
                      {contract.quality_rules_count}
                    </div>
                    <div className="text-slate-500 text-xs">Quality Rules</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-violet-400">
                      {contract.service_levels_count}
                    </div>
                    <div className="text-slate-500 text-xs">SLAs</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-amber-400">
                      {contract.stakeholders_count}
                    </div>
                    <div className="text-slate-500 text-xs">Stakeholders</div>
                  </div>
                </div>
              </div>
            </Card>
            </Link>
          ))}
        </div>
      )}

      {/* Info Card */}
      <Card className="bg-slate-800/30">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-cyan-500/10 rounded-lg">
            <FileText className="w-6 h-6 text-cyan-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white">About ODCS Contracts</h3>
            <p className="text-sm text-slate-400 mt-1">
              ODCS (Open Data Contract Standard) contracts define dataset schemas, quality rules, 
              SLAs, and ownership in a standardized format. Baselinr uses these contracts to 
              automatically configure profiling, validation, and drift detection.
            </p>
            <a
              href="https://bitol-io.github.io/open-data-contract-standard/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-cyan-400 hover:text-cyan-300 text-sm mt-3"
            >
              <ExternalLink className="w-4 h-4" />
              View ODCS Documentation
            </a>
          </div>
        </div>
      </Card>
    </div>
  )
}


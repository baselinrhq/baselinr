'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  ChevronRight, 
  Save, 
  AlertCircle, 
  CheckCircle, 
  Loader2,
  FileText,
  Shield,
  Trash2,
  Edit
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { getContract, updateContract, deleteContract, validateContracts } from '@/lib/api/contracts'
import { ODCSContract } from '@/types/odcs'
import { useRouter } from 'next/navigation'
import { toYAML, parseYAML } from '@/lib/utils/yaml'

interface ContractDetailClientProps {
  contractId: string
}

export default function ContractDetailClient({ contractId }: ContractDetailClientProps) {
  const router = useRouter()
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [editedContract, setEditedContract] = useState<ODCSContract | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [validationResult, setValidationResult] = useState<{ valid: boolean; errors: string[] } | null>(null)
  const [yamlContent, setYamlContent] = useState('')

  // Fetch contract
  const {
    data: contractData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['contract', contractId],
    queryFn: () => getContract(contractId),
    enabled: !!contractId,
  })

  const contract = contractData?.contract

  // Initialize edited contract when contract loads
  useEffect(() => {
    if (contract && !editedContract) {
      const cloned = JSON.parse(JSON.stringify(contract)) // Deep clone
      setEditedContract(cloned)
      try {
        setYamlContent(toYAML(cloned))
      } catch (error) {
        console.error('Failed to convert contract to YAML:', error)
        setYamlContent('')
      }
    }
  }, [contract, editedContract])

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (updatedContract: ODCSContract) => updateContract(contractId, updatedContract),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract', contractId] })
      queryClient.invalidateQueries({ queryKey: ['contracts'] })
      setSaveSuccess(true)
      setIsEditing(false)
      setTimeout(() => setSaveSuccess(false), 3000)
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => deleteContract(contractId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] })
      router.push('/config/contracts')
    },
  })


  const handleSave = async () => {
    if (!yamlContent.trim()) return
    
    try {
      // Parse YAML to contract object
      const parsed = parseYAML(yamlContent) as ODCSContract
      await updateMutation.mutateAsync(parsed)
    } catch (error) {
      setValidationResult({
        valid: false,
        errors: [error instanceof Error ? error.message : 'Failed to parse YAML'],
      })
    }
  }

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this contract? This action cannot be undone.')) {
      await deleteMutation.mutateAsync()
    }
  }

  const handleValidate = async () => {
    try {
      // Use the validate all endpoint with contract filter, or validate the contract directly
      const result = await validateContracts(false)
      // Filter results for this contract
      const contractErrors = result.errors.filter(e => e.contract === contractId)
      
      setValidationResult({
        valid: contractErrors.length === 0,
        errors: contractErrors.map(e => e.message),
      })
    } catch (error) {
      setValidationResult({
        valid: false,
        errors: [error instanceof Error ? error.message : 'Validation failed'],
      })
    }
  }

  const handleEdit = () => {
    if (contract) {
      const cloned = JSON.parse(JSON.stringify(contract))
      setEditedContract(cloned)
      try {
        setYamlContent(toYAML(cloned))
      } catch (error) {
        console.error('Failed to convert contract to YAML:', error)
      }
      setIsEditing(true)
    }
  }

  const handleCancel = () => {
    if (contract) {
      const cloned = JSON.parse(JSON.stringify(contract))
      setEditedContract(cloned)
      try {
        setYamlContent(toYAML(cloned))
      } catch (error) {
        console.error('Failed to convert contract to YAML:', error)
      }
      setIsEditing(false)
      setValidationResult(null)
    }
  }

  if (isLoading) {
    return (
      <div className="p-6 lg:p-8">
        <div className="text-center py-12">
          <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
          <p className="text-slate-400 mt-4">Loading contract...</p>
        </div>
      </div>
    )
  }

  if (error || !contract) {
    return (
      <div className="p-6 lg:p-8">
        <Card className="border-rose-500/50">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-rose-400" />
            <p className="text-rose-400">
              {error instanceof Error ? error.message : 'Failed to load contract'}
            </p>
          </div>
        </Card>
      </div>
    )
  }

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
            <Link href="/config/contracts" className="hover:text-cyan-400">
              Data Contracts
            </Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-white font-medium">
              {contract.info?.title || contract.info?.name || contractId}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText className="w-6 h-6" />
            {contract.info?.title || contract.info?.name || 'Contract Details'}
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            {contract.info?.description || 'ODCS Data Contract'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {!isEditing ? (
            <>
              <Button
                variant="secondary"
                onClick={handleValidate}
                icon={<Shield className="w-4 h-4" />}
              >
                Validate
              </Button>
              <Button
                variant="secondary"
                onClick={handleEdit}
                icon={<Edit className="w-4 h-4" />}
              >
                Edit
              </Button>
              <Button
                variant="danger"
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                loading={deleteMutation.isPending}
                icon={<Trash2 className="w-4 h-4" />}
              >
                Delete
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="secondary"
                onClick={handleCancel}
                disabled={updateMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={updateMutation.isPending || !editedContract}
                loading={updateMutation.isPending}
                icon={<Save className="w-4 h-4" />}
              >
                Save
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Success Message */}
      {saveSuccess && (
        <Card className="border-emerald-500/50 bg-emerald-500/10">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-emerald-400" />
            <p className="text-emerald-300">Contract saved successfully</p>
          </div>
        </Card>
      )}

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
                {validationResult.valid ? 'Contract Valid' : 'Validation Errors'}
              </h3>
              {validationResult.errors.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {validationResult.errors.map((error, idx) => (
                    <li key={idx} className="text-sm text-slate-300">
                      {error}
                    </li>
                  ))}
                </ul>
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

      {/* Contract Editor */}
      <Card>
        <div className="p-6">
          {isEditing ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Edit Contract</h3>
                <span className="px-2 py-1 text-xs rounded bg-amber-500/20 text-amber-400">
                  Editing
                </span>
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-medium text-slate-300">
                  Contract YAML
                </label>
                <textarea
                  value={yamlContent}
                  onChange={(e) => setYamlContent(e.target.value)}
                  className="w-full h-[600px] font-mono text-sm bg-slate-900 border border-slate-700 rounded-lg p-4 text-slate-100 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 focus:outline-none resize-none"
                  spellCheck={false}
                />
                <p className="text-xs text-slate-500">
                  Edit the YAML content above. Changes will be saved when you click Save.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Contract Details</h3>
                <span className={`px-2 py-1 text-xs rounded ${
                  contract.info?.status === 'active'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : contract.info?.status === 'draft'
                    ? 'bg-amber-500/20 text-amber-400'
                    : 'bg-slate-500/20 text-slate-400'
                }`}>
                  {contract.info?.status || 'unknown'}
                </span>
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-medium text-slate-300">
                  Contract YAML
                </label>
                <pre className="w-full h-[600px] overflow-auto font-mono text-sm bg-slate-900 border border-slate-700 rounded-lg p-4 text-slate-100">
                  {yamlContent || (() => {
                    try {
                      return toYAML(contract)
                    } catch {
                      return JSON.stringify(contract, null, 2)
                    }
                  })()}
                </pre>
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}


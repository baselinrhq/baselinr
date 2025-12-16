'use client'

import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, ArrowLeft } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { FormField } from '@/components/ui/FormField'
import { createDataset } from '@/lib/api/datasets'
import { DatasetConfig } from '@/types/config'

export interface DatasetWizardProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

export function DatasetWizard({ isOpen, onClose, onSuccess }: DatasetWizardProps) {
  const [step, setStep] = useState(1)
  const [dataset, setDataset] = useState<Partial<DatasetConfig>>({
    database: null,
    schema: null,
    table: null,
  })
  const [saveToFile, setSaveToFile] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const queryClient = useQueryClient()

  const createMutation = useMutation({
    mutationFn: createDataset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] })
      onSuccess?.()
    },
  })

  useEffect(() => {
    if (isOpen) {
      setStep(1)
      setDataset({ database: null, schema: null, table: null })
      setSaveToFile(false)
      setErrors({})
    }
  }, [isOpen])

  const validateStep1 = (): boolean => {
    const newErrors: Record<string, string> = {}
    
    if (!dataset.database && !dataset.schema && !dataset.table) {
      newErrors.general = 'At least one of database, schema, or table must be specified'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleNext = () => {
    if (step === 1) {
      if (validateStep1()) {
        setStep(2)
      }
    }
  }

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1)
    }
  }

  const handleSave = async () => {
    if (!validateStep1()) {
      return
    }

    try {
      await createMutation.mutateAsync({
        config: dataset as DatasetConfig,
        save_to_file: saveToFile,
        file_path: saveToFile && dataset.table ? `${dataset.table}.yml` : undefined,
      })
      onClose()
    } catch (error) {
      setErrors({
        general: error instanceof Error ? error.message : 'Failed to create dataset',
      })
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create Dataset"
      size="lg"
    >
      <div className="space-y-6">
        {/* Step 1: Dataset Identifier */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-medium text-white mb-2">Dataset Identifier</h3>
              <p className="text-sm text-slate-400 mb-4">
                Specify at least one of database, schema, or table to identify this dataset
              </p>
            </div>

            {errors.general && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-sm text-rose-400">
                {errors.general}
              </div>
            )}

            <FormField label="Database (optional)">
              <Input
                value={dataset.database || ''}
                onChange={(e) => setDataset({ ...dataset, database: e.target.value || null })}
                placeholder="e.g., warehouse"
              />
            </FormField>

            <FormField label="Schema (optional)">
              <Input
                value={dataset.schema || ''}
                onChange={(e) => setDataset({ ...dataset, schema: e.target.value || null })}
                placeholder="e.g., public"
              />
            </FormField>

            <FormField label="Table (optional)">
              <Input
                value={dataset.table || ''}
                onChange={(e) => setDataset({ ...dataset, table: e.target.value || null })}
                placeholder="e.g., customers"
              />
            </FormField>
          </div>
        )}

        {/* Step 2: Save Options */}
        {step === 2 && (
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-medium text-white mb-2">Save Options</h3>
              <p className="text-sm text-slate-400 mb-4">
                Choose where to save this dataset configuration
              </p>
            </div>

            <div className="space-y-3">
              <label className="flex items-start gap-3 p-4 rounded-lg border border-slate-700 cursor-pointer hover:border-slate-600 transition-colors">
                <input
                  type="radio"
                  name="saveOption"
                  checked={!saveToFile}
                  onChange={() => setSaveToFile(false)}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="font-medium text-white">Inline Configuration</div>
                  <div className="text-sm text-slate-400 mt-1">
                    Save in the main config.yml file
                  </div>
                </div>
              </label>

              <label className="flex items-start gap-3 p-4 rounded-lg border border-slate-700 cursor-pointer hover:border-slate-600 transition-colors">
                <input
                  type="radio"
                  name="saveOption"
                  checked={saveToFile}
                  onChange={() => setSaveToFile(true)}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="font-medium text-white">File-based Configuration</div>
                  <div className="text-sm text-slate-400 mt-1">
                    Save as a separate YAML file in the datasets directory
                  </div>
                </div>
              </label>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-700">
          <div className="flex items-center gap-2">
            {step > 1 && (
              <Button
                variant="outline"
                onClick={handleBack}
                icon={<ArrowLeft className="w-4 h-4" />}
              >
                Back
              </Button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            {step < 2 ? (
              <Button
                onClick={handleNext}
                icon={<ArrowRight className="w-4 h-4" />}
              >
                Next
              </Button>
            ) : (
              <Button
                onClick={handleSave}
                disabled={createMutation.isPending}
                loading={createMutation.isPending}
              >
                Create Dataset
              </Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  )
}


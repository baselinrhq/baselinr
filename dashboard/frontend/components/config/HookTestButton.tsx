'use client'

import { useState } from 'react'
import { TestTube, CheckCircle, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { HookConfig } from '@/types/config'
import { testHook, HookTestError } from '@/lib/api/hooks'

export interface HookTestButtonProps {
  hookId: string
  hook?: HookConfig | null
  onTestComplete?: (success: boolean, message: string) => void
}

export function HookTestButton({
  hookId,
  hook,
  onTestComplete,
}: HookTestButtonProps) {
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<{
    success: boolean
    message: string
  } | null>(null)

  const handleTest = async () => {
    setIsTesting(true)
    setTestResult(null)

    try {
      const result = await testHook(hookId, hook || undefined)
      setTestResult({
        success: result.success,
        message: result.message,
      })
      onTestComplete?.(result.success, result.message)
    } catch (error) {
      const message =
        error instanceof HookTestError
          ? error.message
          : error instanceof Error
          ? error.message
          : 'Test failed'
      setTestResult({
        success: false,
        message,
      })
      onTestComplete?.(false, message)
    } finally {
      setIsTesting(false)
    }
  }

  return (
    <div className="space-y-2">
      <Button
        variant="outline"
        size="sm"
        icon={<TestTube className="w-4 h-4" />}
        onClick={handleTest}
        loading={isTesting}
        disabled={isTesting}
      >
        {isTesting ? 'Testing...' : 'Test Hook'}
      </Button>

      {testResult && (
        <div
          className={`flex items-start gap-2 p-3 rounded-lg text-sm ${
            testResult.success
              ? 'glass-card border-emerald-500/30 bg-emerald-500/10 text-emerald-200'
              : 'glass-card border-rose-500/30 bg-rose-500/10 text-rose-200'
          }`}
        >
          {testResult.success ? (
            <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          ) : (
            <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <div className="font-medium">
              {testResult.success ? 'Test Successful' : 'Test Failed'}
            </div>
            <div className="mt-1">{testResult.message}</div>
          </div>
        </div>
      )}
    </div>
  )
}

export default HookTestButton


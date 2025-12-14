import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import FailureSamples from '@/components/validation/FailureSamples'
import { fetchValidationFailureSamples } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  fetchValidationFailureSamples: vi.fn(),
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('FailureSamples', () => {
  const mockSamples = {
    result_id: 1,
    total_failures: 5,
    sample_failures: [
      {
        row_id: 1,
        email: 'invalid-email',
        failure_reason: 'Invalid format',
      },
      {
        row_id: 2,
        email: 'bad@',
        failure_reason: 'Invalid format',
      },
    ],
    failure_patterns: {
      common_pattern: 'missing @ symbol',
    },
  }

  it('renders failure samples table', async () => {
    vi.mocked(fetchValidationFailureSamples).mockResolvedValue(mockSamples)

    render(
      <FailureSamples resultId={1} isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument() // Total failures
      expect(screen.getByText('invalid-email')).toBeInTheDocument()
      expect(screen.getByText('bad@')).toBeInTheDocument()
    })
  })

  it('displays failure reasons', async () => {
    vi.mocked(fetchValidationFailureSamples).mockResolvedValue(mockSamples)

    render(
      <FailureSamples resultId={1} isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      // There are multiple rows with the same failure reason, so use getAllByText
      const failureReasons = screen.getAllByText('Invalid format')
      expect(failureReasons.length).toBeGreaterThan(0)
    })
  })

  it('displays failure patterns if available', async () => {
    vi.mocked(fetchValidationFailureSamples).mockResolvedValue(mockSamples)

    render(
      <FailureSamples resultId={1} isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(screen.getByText(/failure patterns/i)).toBeInTheDocument()
    })
  })

  it('displays empty state when no samples', async () => {
    const emptySamples = {
      result_id: 1,
      total_failures: 0,
      sample_failures: [],
    }

    vi.mocked(fetchValidationFailureSamples).mockResolvedValue(emptySamples)

    render(
      <FailureSamples resultId={1} isOpen={true} onClose={vi.fn()} />,
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(screen.getByText(/no sample failures available/i)).toBeInTheDocument()
    })
  })

  it('calls onClose when close button is clicked', async () => {
    vi.mocked(fetchValidationFailureSamples).mockResolvedValue(mockSamples)
    const onClose = vi.fn()

    render(
      <FailureSamples resultId={1} isOpen={true} onClose={onClose} />,
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      const closeButton = screen.getByRole('button', { name: /close/i })
      closeButton.click()
    })

    // Wait for the modal's exit animation timeout (150ms) before onClose is called
    await waitFor(
      () => {
      expect(onClose).toHaveBeenCalled()
      },
      { timeout: 300 }
    )
  })
})


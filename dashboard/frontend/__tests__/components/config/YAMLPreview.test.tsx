/**
 * Unit tests for YAMLPreview component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'
import { YAMLPreview } from '@/components/config/YAMLPreview'

// Mock Monaco Editor - return component directly
vi.mock('@monaco-editor/react', () => {
  const MockMonacoEditor = ({ value, onChange, onMount }: any) => {
    React.useEffect(() => {
      if (onMount) {
        onMount({}, { languages: { setLanguageConfiguration: vi.fn() } })
      }
    }, [onMount])
    
    return (
      <div data-testid="monaco-editor">
        <textarea
          data-testid="yaml-editor"
          value={value}
          onChange={(e) => onChange && onChange(e.target.value)}
        />
      </div>
    )
  }
  
  return {
    default: MockMonacoEditor,
  }
})

// Mock next/dynamic to return the component immediately without loading state
vi.mock('next/dynamic', () => {
  const MockMonacoEditor = ({ value, onChange, onMount }: any) => {
    React.useEffect(() => {
      if (onMount) {
        onMount({}, { languages: { setLanguageConfiguration: vi.fn() } })
      }
    }, [onMount])
    
    return (
      <div data-testid="monaco-editor">
        <textarea
          data-testid="yaml-editor"
          value={value}
          onChange={(e) => onChange && onChange(e.target.value)}
        />
      </div>
    )
  }
  
  return {
    default: () => MockMonacoEditor,
  }
})

describe('YAMLPreview', () => {
  const mockYAML = `environment: development
source:
  type: postgres
  database: test_db
`

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders YAML preview title', () => {
    render(<YAMLPreview yaml={mockYAML} />)
    expect(screen.getByText('YAML Preview')).toBeInTheDocument()
  })

  it('displays YAML content', () => {
    render(<YAMLPreview yaml={mockYAML} />)
    // Component should render
    expect(screen.getByText('YAML Preview')).toBeInTheDocument()
    // Editor should be available immediately with our mock
    expect(screen.getByTestId('monaco-editor')).toBeInTheDocument()
    const editor = screen.getByTestId('yaml-editor')
    expect(editor).toHaveValue(mockYAML)
  })

  it('calls onChange when YAML is edited', () => {
    const mockOnChange = vi.fn()
    render(<YAMLPreview yaml={mockYAML} onChange={mockOnChange} />)
    
    // Editor should be available immediately with our mock
    const editor = screen.getByTestId('yaml-editor')
    fireEvent.change(editor, { target: { value: 'new yaml content' } })
    
    // onChange should be called
    expect(mockOnChange).toHaveBeenCalledWith('new yaml content')
  })

  it('shows copy button', () => {
    render(<YAMLPreview yaml={mockYAML} />)
    expect(screen.getByText('Copy')).toBeInTheDocument()
  })

  it('shows format button when not read-only', () => {
    render(<YAMLPreview yaml={mockYAML} readOnly={false} />)
    expect(screen.getByText('Format')).toBeInTheDocument()
  })

  it('hides format button when read-only', () => {
    render(<YAMLPreview yaml={mockYAML} readOnly={true} />)
    expect(screen.queryByText('Format')).not.toBeInTheDocument()
  })

  it('displays validation errors', () => {
    const errors = [
      { line: 1, message: 'Invalid syntax' },
      { line: 5, message: 'Missing required field' },
    ]
    render(<YAMLPreview yaml={mockYAML} errors={errors} />)
    
    expect(screen.getByText(/validation error/i)).toBeInTheDocument()
    expect(screen.getByText(/Line 1: Invalid syntax/)).toBeInTheDocument()
    expect(screen.getByText(/Line 5: Missing required field/)).toBeInTheDocument()
  })

  it('handles copy to clipboard', async () => {
    // Mock clipboard API
    const mockWriteText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: mockWriteText },
      writable: true,
      configurable: true,
    })
    
    render(<YAMLPreview yaml={mockYAML} />)
    
    // Wait for component to fully render
    await waitFor(() => {
      expect(screen.getByText('Copy')).toBeInTheDocument()
    })
    
    const copyButton = screen.getByText('Copy')
    fireEvent.click(copyButton)
    
    await waitFor(() => {
      expect(mockWriteText).toHaveBeenCalledWith(mockYAML)
    })
  })

  it('shows copied state after copy', async () => {
    // Mock clipboard API
    const mockWriteText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: mockWriteText },
      writable: true,
      configurable: true,
    })
    
    render(<YAMLPreview yaml={mockYAML} />)
    
    // Wait for component to fully render
    await waitFor(() => {
      expect(screen.getByText('Copy')).toBeInTheDocument()
    })
    
    const copyButton = screen.getByText('Copy')
    fireEvent.click(copyButton)
    
    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeInTheDocument()
    })
  })

  it('handles format button click', () => {
    const mockOnChange = vi.fn()
    render(<YAMLPreview yaml={mockYAML} onChange={mockOnChange} />)
    
    const formatButton = screen.getByText('Format')
    fireEvent.click(formatButton)
    
    // Format should call onChange with formatted YAML
    expect(mockOnChange).toHaveBeenCalled()
  })

  it('syncs external yaml prop to editor', () => {
    const { rerender } = render(<YAMLPreview yaml={mockYAML} />)
    
    const newYAML = 'new: yaml\ncontent: here'
    rerender(<YAMLPreview yaml={newYAML} />)
    
    // Component should re-render (basic smoke test)
    expect(screen.getByText('YAML Preview')).toBeInTheDocument()
  })
})

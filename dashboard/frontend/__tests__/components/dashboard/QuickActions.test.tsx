import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import QuickActions from '@/components/dashboard/QuickActions'

describe('QuickActions', () => {
  it('renders all quick action buttons', () => {
    render(<QuickActions />)
    
    expect(screen.getByText(/Start New Run/i)).toBeInTheDocument()
    expect(screen.getByText(/View All Alerts/i)).toBeInTheDocument()
    expect(screen.getByText(/Configure Validation/i)).toBeInTheDocument()
    expect(screen.getByText(/View Recommendations/i)).toBeInTheDocument()
  })

  it('has correct links for each action', () => {
    render(<QuickActions />)
    
    const startRunLink = screen.getByText(/Start New Run/i).closest('a')
    expect(startRunLink).toHaveAttribute('href', '/runs')
    
    const viewAlertsLink = screen.getByText(/View All Alerts/i).closest('a')
    expect(viewAlertsLink).toHaveAttribute('href', '/drift')
    
    const configValidationLink = screen.getByText(/Configure Validation/i).closest('a')
    expect(configValidationLink).toHaveAttribute('href', '/config/validation')
    
    const viewRecommendationsLink = screen.getByText(/View Recommendations/i).closest('a')
    expect(viewRecommendationsLink).toHaveAttribute('href', '/recommendations')
  })
})


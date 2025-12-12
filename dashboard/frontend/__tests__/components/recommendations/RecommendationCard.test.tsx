/**
 * Unit tests for RecommendationCard component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import RecommendationCard from '@/components/recommendations/RecommendationCard'
import type { TableRecommendation } from '@/types/recommendation'

const mockRecommendation: TableRecommendation = {
  schema: 'public',
  table: 'users',
  confidence: 0.85,
  score: 0.9,
  reasons: ['High query frequency', 'Recent activity'],
  warnings: [],
  suggested_checks: ['completeness', 'freshness'],
  column_recommendations: [],
  low_confidence_columns: [],
  query_count: 100,
  queries_per_day: 10.0,
  row_count: 1000,
  column_count: 5,
  lineage_score: 0.0,
}

describe('RecommendationCard', () => {
  it('renders recommendation card with basic information', () => {
    const onSelect = vi.fn()
    const onApply = vi.fn()

    render(
      <RecommendationCard
        recommendation={mockRecommendation}
        isSelected={false}
        onSelect={onSelect}
        onApply={onApply}
      />
    )

    expect(screen.getByText('users')).toBeInTheDocument()
    expect(screen.getByText(/High Confidence/i)).toBeInTheDocument()
    expect(screen.getByText(/85%/i)).toBeInTheDocument()
  })

  it('calls onSelect when checkbox is clicked', () => {
    const onSelect = vi.fn()
    const onApply = vi.fn()

    render(
      <RecommendationCard
        recommendation={mockRecommendation}
        isSelected={false}
        onSelect={onSelect}
        onApply={onApply}
      />
    )

    const checkbox = screen.getByRole('checkbox')
    fireEvent.click(checkbox)

    expect(onSelect).toHaveBeenCalledTimes(1)
  })

  it('calls onApply when Apply button is clicked', () => {
    const onSelect = vi.fn()
    const onApply = vi.fn()

    render(
      <RecommendationCard
        recommendation={mockRecommendation}
        isSelected={false}
        onSelect={onSelect}
        onApply={onApply}
      />
    )

    const applyButton = screen.getByText('Apply')
    fireEvent.click(applyButton)

    expect(onApply).toHaveBeenCalledTimes(1)
  })

  it('expands to show details when More button is clicked', () => {
    const onSelect = vi.fn()
    const onApply = vi.fn()

    render(
      <RecommendationCard
        recommendation={mockRecommendation}
        isSelected={false}
        onSelect={onSelect}
        onApply={onApply}
      />
    )

    const moreButton = screen.getByText('More')
    fireEvent.click(moreButton)

    expect(screen.getByText('Reasons')).toBeInTheDocument()
    expect(screen.getByText('High query frequency')).toBeInTheDocument()
  })

  it('shows warnings when present', () => {
    const recommendationWithWarnings: TableRecommendation = {
      ...mockRecommendation,
      warnings: ['Low confidence', 'Limited data'],
    }

    const onSelect = vi.fn()
    const onApply = vi.fn()

    render(
      <RecommendationCard
        recommendation={recommendationWithWarnings}
        isSelected={false}
        onSelect={onSelect}
        onApply={onApply}
      />
    )

    const moreButton = screen.getByText('More')
    fireEvent.click(moreButton)

    expect(screen.getByText('Warnings')).toBeInTheDocument()
    expect(screen.getByText('Low confidence')).toBeInTheDocument()
  })

  it('displays metadata correctly', () => {
    const onSelect = vi.fn()
    const onApply = vi.fn()

    render(
      <RecommendationCard
        recommendation={mockRecommendation}
        isSelected={false}
        onSelect={onSelect}
        onApply={onApply}
      />
    )

    const moreButton = screen.getByText('More')
    fireEvent.click(moreButton)

    expect(screen.getByText('100')).toBeInTheDocument() // query_count
    expect(screen.getByText('1,000')).toBeInTheDocument() // row_count
    expect(screen.getByText('5')).toBeInTheDocument() // column_count
  })
})


# Testing

This directory contains unit tests for the Baselinr dashboard frontend.

## Running Tests

```bash
# Run tests in watch mode (recommended for development)
npm test

# Run tests with UI
npm run test:ui

# Run tests once (for CI)
npm run test:run
```

## Test Structure

- `store/` - Tests for Zustand stores
- `hooks/` - Tests for React hooks
- `components/` - Tests for React components (to be added)

## Writing Tests

Tests use:
- **Vitest** - Test runner
- **React Testing Library** - Component testing utilities
- **@testing-library/jest-dom** - DOM matchers

### Example Test

```typescript
import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'

describe('MyComponent', () => {
  it('should work correctly', () => {
    const { result } = renderHook(() => useMyHook())
    expect(result.current.value).toBe('expected')
  })
})
```

## Coverage

To generate coverage reports:

```bash
npm run test:run -- --coverage
```


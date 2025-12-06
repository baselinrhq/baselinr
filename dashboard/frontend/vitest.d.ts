/// <reference types="vitest" />
/// <reference types="@testing-library/jest-dom" />

import { expect, afterEach } from 'vitest'
import * as matchers from '@testing-library/jest-dom/matchers'

declare module 'vitest' {
  interface Assertion<T = any> extends jest.Matchers<void, T> {}
  interface AsymmetricMatchersContaining extends jest.AsymmetricMatchers {}
}


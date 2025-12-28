/**
 * API client for Baselinr ODCS contracts endpoints
 */

import {
  ODCSContract,
  ContractSummary,
  ContractValidationResult,
  ValidationRuleFromContract,
} from '@/types/odcs'
import { getApiUrl } from '../demo-mode'

const API_URL = getApiUrl()

/**
 * Custom error class for contract API errors
 */
export class ContractError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: unknown
  ) {
    super(message)
    this.name = 'ContractError'
  }
}

/**
 * Helper function to parse API error responses
 */
async function parseErrorResponse(response: Response): Promise<string> {
  try {
    const errorData = await response.json()
    return errorData.detail || errorData.message || errorData.error || response.statusText
  } catch {
    return response.statusText
  }
}

/**
 * List all contracts
 */
export async function listContracts(): Promise<{ contracts: ContractSummary[], total: number }> {
  const url = `${API_URL}/api/contracts`
  
  try {
    const response = await fetch(url)
    
    if (!response.ok) {
      const errorMsg = await parseErrorResponse(response)
      throw new ContractError(errorMsg, response.status)
    }
    
    return await response.json()
  } catch (error) {
    if (error instanceof ContractError) {
      throw error
    }
    throw new ContractError(
      error instanceof Error ? error.message : 'Failed to list contracts',
      undefined,
      error
    )
  }
}

/**
 * Get a specific contract by ID
 */
export async function getContract(contractId: string): Promise<{ contract: ODCSContract }> {
  const url = `${API_URL}/api/contracts/${encodeURIComponent(contractId)}`
  
  try {
    const response = await fetch(url)
    
    if (!response.ok) {
      const errorMsg = await parseErrorResponse(response)
      throw new ContractError(errorMsg, response.status)
    }
    
    return await response.json()
  } catch (error) {
    if (error instanceof ContractError) {
      throw error
    }
    throw new ContractError(
      error instanceof Error ? error.message : 'Failed to get contract',
      undefined,
      error
    )
  }
}

/**
 * Create a new contract
 */
export async function createContract(contract: ODCSContract): Promise<{ contract: ODCSContract }> {
  const url = `${API_URL}/api/contracts`
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ contract }),
    })
    
    if (!response.ok) {
      const errorMsg = await parseErrorResponse(response)
      throw new ContractError(errorMsg, response.status)
    }
    
    return await response.json()
  } catch (error) {
    if (error instanceof ContractError) {
      throw error
    }
    throw new ContractError(
      error instanceof Error ? error.message : 'Failed to create contract',
      undefined,
      error
    )
  }
}

/**
 * Update an existing contract
 */
export async function updateContract(
  contractId: string,
  contract: ODCSContract
): Promise<{ contract: ODCSContract }> {
  const url = `${API_URL}/api/contracts/${encodeURIComponent(contractId)}`
  
  try {
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ contract }),
    })
    
    if (!response.ok) {
      const errorMsg = await parseErrorResponse(response)
      throw new ContractError(errorMsg, response.status)
    }
    
    return await response.json()
  } catch (error) {
    if (error instanceof ContractError) {
      throw error
    }
    throw new ContractError(
      error instanceof Error ? error.message : 'Failed to update contract',
      undefined,
      error
    )
  }
}

/**
 * Delete a contract
 */
export async function deleteContract(contractId: string): Promise<void> {
  const url = `${API_URL}/api/contracts/${encodeURIComponent(contractId)}`
  
  try {
    const response = await fetch(url, {
      method: 'DELETE',
    })
    
    if (!response.ok) {
      const errorMsg = await parseErrorResponse(response)
      throw new ContractError(errorMsg, response.status)
    }
  } catch (error) {
    if (error instanceof ContractError) {
      throw error
    }
    throw new ContractError(
      error instanceof Error ? error.message : 'Failed to delete contract',
      undefined,
      error
    )
  }
}

/**
 * Validate contracts
 */
export async function validateContracts(strict: boolean = false): Promise<ContractValidationResult> {
  const url = `${API_URL}/api/contracts/validate?strict=${strict}`
  
  try {
    const response = await fetch(url)
    
    if (!response.ok) {
      const errorMsg = await parseErrorResponse(response)
      throw new ContractError(errorMsg, response.status)
    }
    
    return await response.json()
  } catch (error) {
    if (error instanceof ContractError) {
      throw error
    }
    throw new ContractError(
      error instanceof Error ? error.message : 'Failed to validate contracts',
      undefined,
      error
    )
  }
}

/**
 * Validate a specific contract
 */
export async function validateContract(contractId: string): Promise<ContractValidationResult> {
  const url = `${API_URL}/api/contracts/${encodeURIComponent(contractId)}/validate`
  
  try {
    const response = await fetch(url)
    
    if (!response.ok) {
      const errorMsg = await parseErrorResponse(response)
      throw new ContractError(errorMsg, response.status)
    }
    
    return await response.json()
  } catch (error) {
    if (error instanceof ContractError) {
      throw error
    }
    throw new ContractError(
      error instanceof Error ? error.message : 'Failed to validate contract',
      undefined,
      error
    )
  }
}

/**
 * Get validation rules from a contract
 */
export async function getContractRules(contractId: string): Promise<{ rules: ValidationRuleFromContract[], total: number }> {
  const url = `${API_URL}/api/contracts/${encodeURIComponent(contractId)}/rules`
  
  try {
    const response = await fetch(url)
    
    if (!response.ok) {
      const errorMsg = await parseErrorResponse(response)
      throw new ContractError(errorMsg, response.status)
    }
    
    return await response.json()
  } catch (error) {
    if (error instanceof ContractError) {
      throw error
    }
    throw new ContractError(
      error instanceof Error ? error.message : 'Failed to get contract rules',
      undefined,
      error
    )
  }
}


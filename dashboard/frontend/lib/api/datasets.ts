/**
 * API client for Baselinr dataset endpoints
 */

import {
  DatasetListResponse,
  DatasetConfigResponse,
  CreateDatasetRequest,
  UpdateDatasetRequest,
  DatasetPreviewResponse,
  DatasetValidationResponse,
  DatasetFileListResponse,
  DatasetFileContentResponse,
  CreateDatasetFileRequest,
  UpdateDatasetFileRequest,
  DatasetConfig,
} from '@/types/config'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Custom error class for dataset API errors
 */
export class DatasetError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: unknown
  ) {
    super(message)
    this.name = 'DatasetError'
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
 * List all datasets
 */
export async function listDatasets(): Promise<DatasetListResponse> {
  try {
    const url = `${API_URL}/api/config/datasets`
    const response = await fetch(url)

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new DatasetError(
        `Failed to list datasets: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof DatasetError) {
      throw error
    }
    throw new DatasetError(
      `Failed to list datasets: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Get specific dataset
 */
export async function getDataset(datasetId: string): Promise<DatasetConfigResponse> {
  try {
    const url = `${API_URL}/api/config/datasets/${encodeURIComponent(datasetId)}`
    const response = await fetch(url)

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new DatasetError(
        `Failed to get dataset: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof DatasetError) {
      throw error
    }
    throw new DatasetError(
      `Failed to get dataset: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Create new dataset
 */
export async function createDataset(request: CreateDatasetRequest): Promise<DatasetConfigResponse> {
  try {
    const url = `${API_URL}/api/config/datasets`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new DatasetError(
        `Failed to create dataset: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof DatasetError) {
      throw error
    }
    throw new DatasetError(
      `Failed to create dataset: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Update dataset
 */
export async function updateDataset(
  datasetId: string,
  request: UpdateDatasetRequest
): Promise<DatasetConfigResponse> {
  try {
    const url = `${API_URL}/api/config/datasets/${encodeURIComponent(datasetId)}`
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new DatasetError(
        `Failed to update dataset: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof DatasetError) {
      throw error
    }
    throw new DatasetError(
      `Failed to update dataset: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Delete dataset
 */
export async function deleteDataset(datasetId: string): Promise<void> {
  try {
    const url = `${API_URL}/api/config/datasets/${encodeURIComponent(datasetId)}`
    const response = await fetch(url, {
      method: 'DELETE',
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new DatasetError(
        `Failed to delete dataset: ${errorMessage}`,
        response.status
      )
    }
  } catch (error) {
    if (error instanceof DatasetError) {
      throw error
    }
    throw new DatasetError(
      `Failed to delete dataset: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Get dataset preview (merged config)
 */
export async function getDatasetPreview(datasetId: string): Promise<DatasetPreviewResponse> {
  try {
    const url = `${API_URL}/api/config/datasets/${encodeURIComponent(datasetId)}/preview`
    const response = await fetch(url, {
      method: 'POST',
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new DatasetError(
        `Failed to get dataset preview: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof DatasetError) {
      throw error
    }
    throw new DatasetError(
      `Failed to get dataset preview: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Validate dataset
 */
export async function validateDataset(
  datasetId: string,
  config?: DatasetConfig
): Promise<DatasetValidationResponse> {
  try {
    const url = `${API_URL}/api/config/datasets/${encodeURIComponent(datasetId)}/validate`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config ? { config } : {}),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new DatasetError(
        `Failed to validate dataset: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof DatasetError) {
      throw error
    }
    throw new DatasetError(
      `Failed to validate dataset: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * List dataset files
 */
export async function listDatasetFiles(): Promise<DatasetFileListResponse> {
  try {
    const url = `${API_URL}/api/config/datasets/files`
    const response = await fetch(url)

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new DatasetError(
        `Failed to list files: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof DatasetError) {
      throw error
    }
    throw new DatasetError(
      `Failed to list files: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Get dataset file content
 */
export async function getDatasetFile(filePath: string): Promise<DatasetFileContentResponse> {
  try {
    const url = `${API_URL}/api/config/datasets/files/${encodeURIComponent(filePath)}`
    const response = await fetch(url)

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new DatasetError(
        `Failed to get file: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof DatasetError) {
      throw error
    }
    throw new DatasetError(
      `Failed to get file: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Create dataset file
 */
export async function createDatasetFile(request: CreateDatasetFileRequest): Promise<DatasetFileContentResponse> {
  try {
    const url = `${API_URL}/api/config/datasets/files`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new DatasetError(
        `Failed to create file: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof DatasetError) {
      throw error
    }
    throw new DatasetError(
      `Failed to create file: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Update dataset file
 */
export async function updateDatasetFile(
  filePath: string,
  request: UpdateDatasetFileRequest
): Promise<DatasetFileContentResponse> {
  try {
    const url = `${API_URL}/api/config/datasets/files/${encodeURIComponent(filePath)}`
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new DatasetError(
        `Failed to update file: ${errorMessage}`,
        response.status
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof DatasetError) {
      throw error
    }
    throw new DatasetError(
      `Failed to update file: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Delete dataset file
 */
export async function deleteDatasetFile(filePath: string): Promise<void> {
  try {
    const url = `${API_URL}/api/config/datasets/files/${encodeURIComponent(filePath)}`
    const response = await fetch(url, {
      method: 'DELETE',
    })

    if (!response.ok) {
      const errorMessage = await parseErrorResponse(response)
      throw new DatasetError(
        `Failed to delete file: ${errorMessage}`,
        response.status
      )
    }
  } catch (error) {
    if (error instanceof DatasetError) {
      throw error
    }
    throw new DatasetError(
      `Failed to delete file: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}


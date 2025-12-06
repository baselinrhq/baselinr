/**
 * Unit tests for connections API client
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  listConnections,
  getConnection,
  saveConnection,
  updateConnection,
  deleteConnection,
  ConnectionError,
} from '@/lib/api/connections'
import type { ConnectionConfig } from '@/types/config'
import type { SavedConnection, ConnectionsListResponse } from '@/types/connection'

// Mock fetch globally
global.fetch = vi.fn()

describe('connections API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listConnections', () => {
    it('should list connections successfully', async () => {
      const mockResponse: ConnectionsListResponse = {
        connections: [
          {
            id: '1',
            name: 'Test Connection',
            connection: {
              type: 'postgres',
              database: 'test_db',
            },
            created_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await listConnections()

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/config/connections')
      )
    })

    it('should throw ConnectionError on failure', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Server error' }),
      } as Response)

      await expect(listConnections()).rejects.toThrow(ConnectionError)
    })
  })

  describe('getConnection', () => {
    it('should get connection by ID successfully', async () => {
      const mockConnection: SavedConnection = {
        id: '1',
        name: 'Test Connection',
        connection: {
          type: 'postgres',
          database: 'test_db',
        },
        created_at: '2024-01-01T00:00:00Z',
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockConnection,
      } as Response)

      const result = await getConnection('1')

      expect(result).toEqual(mockConnection)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/config/connections/1')
      )
    })

    it('should throw ConnectionError when connection not found', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'Connection not found' }),
      } as Response)

      await expect(getConnection('999')).rejects.toThrow(ConnectionError)
    })
  })

  describe('saveConnection', () => {
    it('should save connection successfully', async () => {
      const connectionConfig: ConnectionConfig = {
        type: 'postgres',
        host: 'localhost',
        port: 5432,
        database: 'test_db',
      }

      const mockResponse = {
        id: '1',
        connection: {
          id: '1',
          name: 'New Connection',
          connection: connectionConfig,
          created_at: '2024-01-01T00:00:00Z',
        },
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await saveConnection('New Connection', connectionConfig)

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/config/connections'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            name: 'New Connection',
            connection: connectionConfig,
          }),
        })
      )
    })

    it('should throw ConnectionError on validation failure', async () => {
      const connectionConfig: ConnectionConfig = {
        type: 'postgres',
        database: 'test_db',
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ detail: 'Invalid connection config' }),
      } as Response)

      await expect(
        saveConnection('New Connection', connectionConfig)
      ).rejects.toThrow(ConnectionError)
    })
  })

  describe('updateConnection', () => {
    it('should update connection successfully', async () => {
      const connectionConfig: ConnectionConfig = {
        type: 'postgres',
        host: 'newhost',
        port: 5432,
        database: 'test_db',
      }

      const mockResponse = {
        id: '1',
        connection: {
          id: '1',
          name: 'Updated Connection',
          connection: connectionConfig,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-02T00:00:00Z',
        },
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await updateConnection('1', 'Updated Connection', connectionConfig)

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/config/connections/1'),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({
            name: 'Updated Connection',
            connection: connectionConfig,
          }),
        })
      )
    })

    it('should throw ConnectionError when connection not found', async () => {
      const connectionConfig: ConnectionConfig = {
        type: 'postgres',
        database: 'test_db',
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'Connection not found' }),
      } as Response)

      await expect(
        updateConnection('999', 'Updated', connectionConfig)
      ).rejects.toThrow(ConnectionError)
    })
  })

  describe('deleteConnection', () => {
    it('should delete connection successfully', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
      } as Response)

      await deleteConnection('1')

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/config/connections/1'),
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })

    it('should throw ConnectionError when connection not found', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'Connection not found' }),
      } as Response)

      await expect(deleteConnection('999')).rejects.toThrow(ConnectionError)
    })
  })
})


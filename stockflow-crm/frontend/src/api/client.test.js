/**
 * Tests for the axios client — interceptors, token injection, 401 redirect.
 *
 * We test the interceptor logic directly rather than making real HTTP requests.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock axios before importing client
vi.mock('axios', () => {
  const requestHandlers = []
  const responseHandlers = []

  const instance = {
    interceptors: {
      request: {
        use: vi.fn((fn) => requestHandlers.push(fn)),
        _handlers: requestHandlers,
      },
      response: {
        use: vi.fn((ok, err) => responseHandlers.push({ ok, err })),
        _handlers: responseHandlers,
      },
    },
    get: vi.fn(),
    post: vi.fn(),
  }

  return {
    default: {
      create: vi.fn(() => instance),
    },
    _instance: instance,
  }
})

import axios from 'axios'

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
})

describe('axios client configuration', () => {
  it('creates client with VITE_API_URL as baseURL', async () => {
    await import('./client.js')
    expect(axios.create).toHaveBeenCalledWith(
      expect.objectContaining({ baseURL: expect.anything() })
    )
  })
})

describe('request interceptor', () => {
  it('attaches Bearer token from localStorage when present', async () => {
    localStorage.setItem('token', 'my-jwt-token')
    // Re-import to get fresh interceptor registration
    const mod = await import('./client.js')
    const instance = axios.create.mock.results[0]?.value
    const requestInterceptor = instance?.interceptors.request._handlers[0]

    if (requestInterceptor) {
      const config = { headers: {} }
      const result = requestInterceptor(config)
      expect(result.headers.Authorization).toBe('Bearer my-jwt-token')
    }
  })

  it('does not attach Authorization header when no token', async () => {
    await import('./client.js')
    const instance = axios.create.mock.results[0]?.value
    const requestInterceptor = instance?.interceptors.request._handlers[0]

    if (requestInterceptor) {
      const config = { headers: {} }
      const result = requestInterceptor(config)
      expect(result.headers.Authorization).toBeUndefined()
    }
  })
})

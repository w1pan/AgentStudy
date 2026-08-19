import axios from 'axios'

export class ApiError extends Error {
  status: number

  constructor(message: string, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export const client = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const timedOut =
      error.code === 'ECONNABORTED' ||
      error.code === 'ETIMEDOUT' ||
      String(error.message || '').toLowerCase().includes('timeout')
    const message = timedOut
      ? '请求处理时间较长，请稍后重试'
      : error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new ApiError(message, error.response?.status || 0))
  }
)

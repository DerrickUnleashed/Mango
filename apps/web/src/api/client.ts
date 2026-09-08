const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

interface ApiResponse<T> {
  ok: boolean
  status: number
  data?: T
  detail?: string
  code?: string
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  const body = (await response.json().catch(() => ({}))) as unknown

  if (!response.ok) {
    const errBody = body as Partial<ApiResponse<unknown>>
    const status = response.status
    const code = errBody.code || 'internal_error'
    const detail = errBody.detail || `Request failed with status ${status}`
    throw new ApiError(status, code, detail)
  }

  return body as T
}

export async function apiUpload<T>(
  path: string,
  formData: FormData,
  onProgress?: (percent: number) => void,
): Promise<T> {
  if (onProgress) {
    return apiUploadWithProgress<T>(path, formData, onProgress)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    body: formData,
  })
  return handleResponse<T>(response)
}

async function apiUploadWithProgress<T>(
  path: string,
  formData: FormData,
  onProgress: (percent: number) => void,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE_URL}${path}`)

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    }

    xhr.onload = () => {
      try {
        const body = JSON.parse(xhr.responseText) as unknown
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(body as T)
        } else {
          const errBody = body as Partial<ApiResponse<unknown>>
          reject(
            new ApiError(
              xhr.status,
              errBody.code || 'internal_error',
              errBody.detail || 'Upload failed',
            ),
          )
        }
      } catch {
        reject(new ApiError(xhr.status, 'invalid_response', 'Invalid server response'))
      }
    }

    xhr.onerror = () => reject(new ApiError(0, 'network_error', 'Network error'))
    xhr.send(formData)
  })
}

async function handleResponse<T>(response: Response): Promise<T> {
  const body = (await response.json().catch(() => ({}))) as unknown
  if (!response.ok) {
    const errBody = body as Partial<ApiResponse<unknown>>
    throw new ApiError(
      response.status,
      errBody.code || 'internal_error',
      errBody.detail || `Request failed with status ${response.status}`,
    )
  }
  return body as T
}
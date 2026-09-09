import type { SettingsResponse, UpdateSettingsPayload } from '@orchardvision/types'
import { apiRequest } from './client'

export function getSettings(): Promise<SettingsResponse> {
  return apiRequest<SettingsResponse>('/settings')
}

export function updateSettings(
  payload: UpdateSettingsPayload,
): Promise<SettingsResponse> {
  return apiRequest<SettingsResponse>('/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}
import type {
  CreateExperimentRequest,
  Experiment,
  ExperimentListResponse,
} from '@orchardvision/types'
import { apiRequest } from './client'

export function getExperiments(): Promise<ExperimentListResponse> {
  return apiRequest<ExperimentListResponse>('/experiments')
}

export function createExperiment(
  request: CreateExperimentRequest,
): Promise<Experiment> {
  return apiRequest<Experiment>('/experiments', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export function deleteExperiment(id: string): Promise<{ ok: boolean }> {
  return apiRequest<{ ok: boolean }>(`/experiments/${id}`, { method: 'DELETE' })
}
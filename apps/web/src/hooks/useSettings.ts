import { useQuery } from '@tanstack/react-query'
import { getSettings } from '../api/settings'

export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: getSettings,
    staleTime: 30_000,
  })
}

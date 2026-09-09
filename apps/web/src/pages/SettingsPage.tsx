import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { PipelineSettingsValues } from '@orchardvision/types'
import { useToast } from '../components/ui/useToast'
import { getSettings, updateSettings } from '../api/settings'

const DEFAULTS: PipelineSettingsValues = {
  confidenceThreshold: 0.35,
  reidThreshold: 0.6,
  memoryUpdateRate: 0.2,
  occlusionTimeoutSec: 30,
  cameraMotionMode: 'static',
}

export function SettingsPage() {
  const { push } = useToast()
  const queryClient = useQueryClient()
  useQuery({
    queryKey: ['settings'],
    queryFn: getSettings,
    staleTime: 30_000,
  })
  const saveMutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      push('Settings saved', 'success')
    },
    onError: () => {
      push('Failed to save settings', 'error')
    },
  })

  const [values, setValues] = useState<PipelineSettingsValues>(DEFAULTS)
  const [saved, setSaved] = useState(false)

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    saveMutation.mutate(
      { values: valuesToPayload(values) },
      {
        onSuccess: () => setSaved(true),
      },
    )
  }

  const fieldNumber = (key: Exclude<keyof PipelineSettingsValues, 'cameraMotionMode'>) => ({
    value: values[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => {
      const next = e.target.value
      setValues((prev) => ({ ...prev, [key]: Number(next) }))
      setSaved(false)
    },
  })

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-surface-50">Settings</h1>
        <p className="mt-1 text-sm text-surface-400">
          Pipeline and visualization defaults (persisted; applied when process options are left
          unset)
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="rounded-xl border border-surface-800 bg-surface-900/60 p-6">
          <h2 className="mb-4 font-medium text-surface-200">Detector</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-surface-400">
                Confidence threshold
              </span>
              <input
                type="number"
                min={0}
                max={1}
                step={0.05}
                {...fieldNumber('confidenceThreshold')}
                className="w-full rounded-lg border border-surface-700 bg-surface-950 px-3 py-2 text-surface-100 focus:border-orchard-500 focus:outline-none"
              />
            </label>
          </div>
        </section>

        <section className="rounded-xl border border-surface-800 bg-surface-900/60 p-6">
          <h2 className="mb-4 font-medium text-surface-200">Re-Identification</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-surface-400">Re-ID threshold</span>
              <input type="number" min={0} max={1} step={0.05} {...fieldNumber('reidThreshold')}
                className="w-full rounded-lg border border-surface-700 bg-surface-950 px-3 py-2 text-surface-100 focus:border-orchard-500 focus:outline-none" />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-surface-400">
                Occlusion timeout (seconds)
              </span>
              <input type="number" min={1} max={600} {...fieldNumber('occlusionTimeoutSec')}
                className="w-full rounded-lg border border-surface-700 bg-surface-950 px-3 py-2 text-surface-100 focus:border-orchard-500 focus:outline-none" />
            </label>
          </div>
        </section>

        <section className="rounded-xl border border-surface-800 bg-surface-900/60 p-6">
          <h2 className="mb-4 font-medium text-surface-200">Identity Memory</h2>
          <label className="block max-w-xs">
            <span className="mb-1 block text-xs font-medium text-surface-400">Prototype update rate</span>
            <input type="number" min={0} max={1} step={0.05} {...fieldNumber('memoryUpdateRate')}
              className="w-full rounded-lg border border-surface-700 bg-surface-950 px-3 py-2 text-surface-100 focus:border-orchard-500 focus:outline-none" />
          </label>
        </section>

        <section className="rounded-xl border border-surface-800 bg-surface-900/60 p-6">
          <h2 className="mb-4 font-medium text-surface-200">Camera Motion</h2>
          <fieldset>
            <legend className="mb-2 text-xs font-medium text-surface-400">Motion mode</legend>
            <div className="flex flex-wrap gap-3">
              {(['static', 'drift'] as const).map((mode) => (
                <label key={mode} className="inline-flex cursor-pointer items-center gap-2">
                  <input
                    type="radio"
                    name="cameraMotionMode"
                    value={mode}
                    checked={values.cameraMotionMode === mode}
                    onChange={() => {
                      setValues((prev) => ({ ...prev, cameraMotionMode: mode }))
                      setSaved(false)
                    }}
                    className="h-4 w-4 accent-orchard-500"
                  />
                  <span className="text-sm capitalize text-surface-300">{mode}</span>
                </label>
              ))}
            </div>
          </fieldset>
        </section>

        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={saveMutation.isPending}
            className="rounded-lg bg-orchard-600 px-5 py-2 font-medium text-white transition-colors hover:bg-orchard-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orchard-400 disabled:opacity-50"
          >
            {saveMutation.isPending ? 'Saving…' : 'Save settings'}
          </button>
          {saved && (
            <span className="text-sm text-orchard-400" role="status">Saved</span>
          )}
        </div>
      </form>
    </div>
  )
}

function valuesToPayload(values: PipelineSettingsValues): Partial<PipelineSettingsValues> {
  const numeric: PipelineSettingsValues = {
    confidenceThreshold: Number(values.confidenceThreshold),
    reidThreshold: Number(values.reidThreshold),
    memoryUpdateRate: Number(values.memoryUpdateRate),
    occlusionTimeoutSec: Number(values.occlusionTimeoutSec),
    cameraMotionMode: values.cameraMotionMode === 'drift' ? 'drift' : 'static',
  }
  return numeric
}
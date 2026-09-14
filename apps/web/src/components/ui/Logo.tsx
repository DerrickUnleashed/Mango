import { useId } from 'react'

interface LogoMarkProps {
  className?: string
  gradientId?: string
}

export function LogoMark({ className, gradientId }: LogoMarkProps) {
  const autoId = useId()
  const id = gradientId ?? autoId.replace(/:/g, '')
  const bodyId = `mango-body-${id}`
  const leafId = `mango-leaf-${id}`

  return (
    <svg
      viewBox="0 0 32 32"
      aria-hidden="true"
      className={className}
      focusable="false"
    >
      <defs>
        <linearGradient id={bodyId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#FDE047" />
          <stop offset="55%" stopColor="#FBBF24" />
          <stop offset="100%" stopColor="#F97316" />
        </linearGradient>
        <linearGradient id={leafId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#34D399" />
          <stop offset="100%" stopColor="#059669" />
        </linearGradient>
      </defs>
      <ellipse
        cx="16"
        cy="17.6"
        rx="8.2"
        ry="12"
        transform="rotate(36 16 17.6)"
        fill={`url(#${bodyId})`}
      />
      <path
        d="M9.4 8.1 17.4 6.2c2.2-.5 4.3.7 4.9 2.8.5 1.9-.3 3.9-2 4.8-1.7.9-3.8.9-5.4-.2L9.2 9.8c-.6-2 .2-2.1.2-1.7z"
        fill={`url(#${leafId})`}
        opacity="0.96"
      />
      <path
        d="M18.6 5.6c.6-2 3-2.7 4.8-1.5"
        fill="none"
        stroke="#059669"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path
        d="M14.6 4.6c2.4-2 6-1.2 7.8.9-2.3 1.6-5.6 1.6-8 .4z"
        fill="#059669"
        opacity="0.55"
      />
      <path
        d="M10.5 25.4c-1.6-1.4-2.5-4.4-2.1-8.6.4-4 1.6-6.9 3.3-8.2"
        fill="none"
        stroke="#FDE68A"
        strokeWidth="1.3"
        strokeLinecap="round"
        opacity="0.55"
      />
    </svg>
  )
}

export function Logo({ className, markClassName }: { className?: string; markClassName?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className ?? ''}`}>
      <LogoMark className={markClassName ?? 'h-8 w-8'} />
      <span className="font-display text-base font-semibold tracking-tight">OrchardVision</span>
    </span>
  )
}
/**
 * Brand mark + wordmark used on the boot splash, the entry screen and the app shell.
 * Pure inline SVG so it renders with no network access (sandboxed previews included).
 */

export function BrandMark({ size = 48, animate = false }: { size?: number; animate?: boolean }) {
  const uid = `bm${size}${animate ? 'a' : ''}`
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden className={animate ? 'boot-mark' : undefined}>
      <defs>
        <linearGradient id={`${uid}-shield`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#5aa2f7" />
          <stop offset="45%" stopColor="#1a6adb" />
          <stop offset="100%" stopColor="#0b1f45" />
        </linearGradient>
        <linearGradient id={`${uid}-edge`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#c3dcfd" stopOpacity="0.65" />
        </linearGradient>
      </defs>

      {/* shield */}
      <path
        d="M32 4 55 13v17.5C55 44.6 45.4 54.6 32 60 18.6 54.6 9 44.6 9 30.5V13z"
        fill={`url(#${uid}-shield)`}
      />
      <path
        d="M32 4 55 13v17.5C55 44.6 45.4 54.6 32 60 18.6 54.6 9 44.6 9 30.5V13z"
        fill="none" stroke="#ffffff" strokeOpacity="0.28" strokeWidth="1.1"
      />

      {/* evidence network inside the shield */}
      <g stroke={`url(#${uid}-edge)`} strokeWidth="1.6" strokeLinecap="round" fill="none">
        <path className={animate ? 'draw-line' : undefined} d="M23 23.5 41 27" />
        <path className={animate ? 'draw-line' : undefined} style={{ animationDelay: '160ms' }} d="M22.4 25.6 29 41.5" />
        <path className={animate ? 'draw-line' : undefined} style={{ animationDelay: '300ms' }} d="M40.3 29.4 31 41" />
      </g>
      <g fill="#ffffff">
        <circle cx="22" cy="22" r="4.2" fillOpacity="0.96" />
        <circle cx="42" cy="27.5" r="3.4" fillOpacity="0.9" className={animate ? 'node-pulse' : undefined} />
        <circle cx="30" cy="43" r="3.4" fillOpacity="0.9" className={animate ? 'node-pulse' : undefined} style={{ animationDelay: '900ms' }} />
      </g>
      <circle cx="22" cy="22" r="7.4" fill="none" stroke="#ffffff" strokeOpacity="0.3" strokeWidth="1" />
    </svg>
  )
}

export function Wordmark({
  size = 'md', tone = 'dark', className = '',
}: { size?: 'sm' | 'md' | 'lg' | 'xl'; tone?: 'dark' | 'light'; className?: string }) {
  const scale = {
    sm: 'text-[15px]', md: 'text-[22px]', lg: 'text-[34px]', xl: 'text-[46px] sm:text-[58px]',
  }[size]
  const base = tone === 'light' ? 'text-white' : 'text-[var(--color-primary-deep)]'
  const accent = tone === 'light' ? 'text-[var(--color-primary-soft)]' : 'text-[var(--color-primary)]'
  return (
    <span className={`block font-extrabold leading-none tracking-tight ${scale} ${base} ${className}`}>
      CRIMENET <span className={accent}>AI</span>
    </span>
  )
}

export function Tagline({ tone = 'dark', className = '' }: { tone?: 'dark' | 'light'; className?: string }) {
  return (
    <span
      className={`block font-semibold uppercase ${
        tone === 'light' ? 'text-[var(--color-primary-soft)]/90' : 'text-[var(--color-primary)]'
      } ${className}`}
    >
      Evidence <span className="opacity-60">→</span> Relationships <span className="opacity-60">→</span> Analysis{' '}
      <span className="opacity-60">→</span> Validation
    </span>
  )
}

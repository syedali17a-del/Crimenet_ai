import type { SVGProps } from 'react'

type IconName =
  | 'dashboard' | 'cases' | 'evidence' | 'network' | 'timeline' | 'map' | 'crosscase'
  | 'entities' | 'hypotheses' | 'gaps' | 'nextbest' | 'audit' | 'security' | 'search'
  | 'bell' | 'user' | 'menu' | 'close' | 'check' | 'reject' | 'shield' | 'hash' | 'play'
  | 'filter' | 'chevron' | 'alert' | 'info' | 'lock' | 'upload' | 'refresh' | 'link'
  | 'logout' | 'plus' | 'note' | 'clock' | 'target' | 'branch' | 'fit' | 'reset' | 'eye'
  | 'arrowRight' | 'spark' | 'doc' | 'globe'

const paths: Record<IconName, string[]> = {
  globe: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z', 'M3.6 9h16.8', 'M3.6 15h16.8', 'M12 3c2.4 2.4 3.6 5.4 3.6 9S14.4 18.6 12 21c-2.4-2.4-3.6-5.4-3.6-9S9.6 5.4 12 3z'],
  dashboard: ['M3 3h7v8H3z', 'M14 3h7v5h-7z', 'M14 11h7v10h-7z', 'M3 14h7v7H3z'],
  cases: ['M3 7h18v12H3z', 'M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2'],
  evidence: ['M7 3h7l5 5v13H7z', 'M14 3v5h5', 'M10 13h6', 'M10 17h6'],
  network: ['M5 6a2 2 0 1 0 0-.001M19 8a2 2 0 1 0 0-.001M12 18a2 2 0 1 0 0-.001', 'M6.7 7.3 10.7 16.4', 'M17.4 9.4 13.4 16.6', 'M7 6.6 17 7.7'],
  timeline: ['M4 6h16', 'M4 12h16', 'M4 18h16', 'M8 4v4', 'M15 10v4', 'M10 16v4'],
  map: ['M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z', 'M9 4v14', 'M15 6v14'],
  crosscase: ['M4 5h7v6H4z', 'M13 13h7v6h-7z', 'M11 8h4a2 2 0 0 1 2 2v3'],
  entities: ['M12 7a3 3 0 1 0 0-.001', 'M5 20c0-3.5 3.1-6 7-6s7 2.5 7 6'],
  hypotheses: ['M9 18h6', 'M10 21h4', 'M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2h5c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z'],
  gaps: ['M12 3 2 20h20z', 'M12 9v5', 'M12 17.2v.1'],
  nextbest: ['M4 12h10', 'm11 8 4 4-4 4', 'M17 5v14'],
  audit: ['M6 3h12v18l-6-3-6 3z', 'M9 8h6', 'M9 12h6'],
  security: ['M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z', 'm9 12 2 2 4-4'],
  search: ['M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z', 'm16.5 16.5 4 4'],
  bell: ['M6 9a6 6 0 1 1 12 0c0 4 1.5 5.5 1.5 5.5H4.5S6 13 6 9z', 'M10.5 18.5a1.8 1.8 0 0 0 3 0'],
  user: ['M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M4 21c0-3.9 3.6-6.5 8-6.5s8 2.6 8 6.5'],
  menu: ['M4 7h16', 'M4 12h16', 'M4 17h16'],
  close: ['m6 6 12 12', 'm18 6-12 12'],
  check: ['m5 13 4 4L19 7'],
  reject: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z', 'm9 9 6 6', 'm15 9-6 6'],
  shield: ['M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z'],
  hash: ['M5 9h14', 'M5 15h14', 'M10 4 8 20', 'M16 4l-2 16'],
  play: ['m7 5 12 7-12 7z'],
  filter: ['M4 5h16l-6 7v6l-4 2v-8z'],
  chevron: ['m9 6 6 6-6 6'],
  alert: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z', 'M12 8v5', 'M12 16.2v.1'],
  info: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z', 'M12 11v5', 'M12 7.8v.1'],
  lock: ['M6 11h12v9H6z', 'M9 11V8a3 3 0 0 1 6 0v3'],
  upload: ['M12 16V5', 'm8 9 4-4 4 4', 'M5 19h14'],
  refresh: ['M4 12a8 8 0 0 1 13.7-5.6L20 8', 'M20 4v4h-4', 'M20 12a8 8 0 0 1-13.7 5.6L4 16', 'M4 20v-4h4'],
  link: ['M10 13a4 4 0 0 0 5.7 0l2.5-2.5a4 4 0 1 0-5.7-5.7L11 6.3', 'M14 11a4 4 0 0 0-5.7 0L5.8 13.5a4 4 0 1 0 5.7 5.7l1.5-1.5'],
  logout: ['M14 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-2', 'M10 12h11', 'm18 9 3 3-3 3'],
  plus: ['M12 5v14', 'M5 12h14'],
  note: ['M5 4h11l3 3v13H5z', 'M9 10h7', 'M9 14h5'],
  clock: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z', 'M12 7v5l3 2'],
  target: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z', 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z', 'M12 11.5v.1'],
  branch: ['M7 4v10a4 4 0 0 0 4 4h6', 'M7 4a2 2 0 1 0 0 .001', 'M19 18a2 2 0 1 0 0 .001'],
  fit: ['M4 9V4h5', 'M20 9V4h-5', 'M4 15v5h5', 'M20 15v5h-5'],
  reset: ['M4 12a8 8 0 1 1 2.3 5.6', 'M4 20v-5h5'],
  eye: ['M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6-10-6-10-6z', 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z'],
  arrowRight: ['M4 12h15', 'm14 7 5 5-5 5'],
  spark: ['M12 3v4', 'M12 17v4', 'M3 12h4', 'M17 12h4', 'm6 6 2.5 2.5', 'm15.5 15.5 2.5 2.5', 'm18 6-2.5 2.5', 'm8.5 15.5-2.5 2.5'],
  doc: ['M7 3h7l5 5v13H7z', 'M14 3v5h5'],
}

export function Icon({ name, size = 18, ...rest }: { name: IconName; size?: number } & SVGProps<SVGSVGElement>) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...rest}
    >
      {paths[name].map((d, i) => (
        <path key={i} d={d} />
      ))}
    </svg>
  )
}

export type { IconName }

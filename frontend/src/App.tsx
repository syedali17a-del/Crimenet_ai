import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import BootSplash from './components/system/BootSplash'
import AppLayout from './components/layout/AppLayout'
import { useApp } from './state/AppContext'
import { Icon } from './components/shared/Icon'
import { Spinner } from './components/shared/ui'
import { useI18n } from './i18n/LanguageContext'
import LanguageSelect from './pages/LanguageSelect'

import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Workflow from './pages/Workflow'
import Cases from './pages/Cases'
import CaseDetails from './pages/CaseDetails'
import Evidence from './pages/Evidence'
import NetworkIntelligence from './pages/NetworkIntelligence'
import Timeline from './pages/Timeline'
import MapIntelligence from './pages/MapIntelligence'
import CrossCase from './pages/CrossCase'
import EntityResolution from './pages/EntityResolution'
import Hypotheses from './pages/Hypotheses'
import InformationGaps from './pages/InformationGaps'
import NextBestAction from './pages/NextBestAction'
import Audit from './pages/Audit'
import Security from './pages/Security'

function Toaster() {
  const { toasts, dismiss } = useApp()
  const { t: tr } = useI18n()
  if (toasts.length === 0) return null
  const tone = {
    success: 'border-[var(--color-success)] bg-[var(--color-surface-solid)] text-[var(--color-success)]',
    error: 'border-[var(--color-danger)] bg-[var(--color-surface-solid)] text-[var(--color-danger)]',
    info: 'border-[var(--color-primary)] bg-[var(--color-primary-soft)]/95 text-[var(--color-primary-deep)]',
  }
  const icon = { success: 'check', error: 'alert', info: 'info' } as const
  return (
    <div className="pointer-events-none fixed bottom-4 right-3 z-[100] flex w-[min(360px,calc(100vw-24px))] flex-col gap-2">
      {toasts.map((t) => (
        <div key={t.id} className={`fade-in pointer-events-auto flex items-start gap-2 rounded-xl border px-3.5 py-2.5 shadow-[0_18px_40px_-24px_rgba(18,45,94,0.7)] backdrop-blur ${tone[t.kind]}`}>
          <span className="mt-0.5 shrink-0"><Icon name={icon[t.kind]} size={16} /></span>
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-semibold leading-snug">{t.title}</p>
            {t.message && <p className="mt-0.5 break-words text-[12px] leading-snug opacity-85">{t.message}</p>}
          </div>
          <button onClick={() => dismiss(t.id)} className="focus-ring shrink-0 rounded p-0.5 opacity-60 hover:opacity-100" aria-label={tr.common.dismiss}>
            <Icon name="close" size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}

function Protected({ children }: { children: React.ReactNode }) {
  const { user, ready } = useApp()
  const { t } = useI18n()
  const location = useLocation()
  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="glass flex items-center gap-3 rounded-xl px-5 py-4">
          <Spinner size={18} />
          <span className="text-[13px] font-medium text-[var(--color-text)]">{t.common.restoringSession}</span>
        </div>
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <AppLayout>{children}</AppLayout>
}

function Page({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  return <div key={location.pathname} className="page-enter">{children}</div>
}

const BOOT_FLAG = 'crimenet.booted'

export default function App() {
  const { user, ready } = useApp()
  const { chosen, t } = useI18n()
  // The boot sequence runs once per browser tab session: a full page load shows
  // the CrimeNet AI mark while the client performs its real start-up handshake.
  const [booting, setBooting] = useState(() => sessionStorage.getItem(BOOT_FLAG) !== '1')

  useEffect(() => {
    if (!booting) return
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [booting])

  if (booting) {
    return (
      <BootSplash
        onDone={() => {
          sessionStorage.setItem(BOOT_FLAG, '1')
          setBooting(false)
        }}
      />
    )
  }

  // Language selection is the FIRST screen: the login page is not reachable
  // until the investigator has explicitly chosen an interface language.
  if (!chosen) return <LanguageSelect />

  return (
    <>
      <Routes>
        <Route path="/login" element={ready && user ? <Navigate to="/dashboard" replace /> : <Login />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Protected><Page><Dashboard /></Page></Protected>} />
        <Route path="/workflow" element={<Protected><Page><Workflow /></Page></Protected>} />
        <Route path="/cases" element={<Protected><Page><Cases /></Page></Protected>} />
        <Route path="/cases/:caseId" element={<Protected><Page><CaseDetails /></Page></Protected>} />
        <Route path="/evidence" element={<Protected><Page><Evidence /></Page></Protected>} />
        <Route path="/network" element={<Protected><Page><NetworkIntelligence /></Page></Protected>} />
        <Route path="/timeline" element={<Protected><Page><Timeline /></Page></Protected>} />
        <Route path="/map" element={<Protected><Page><MapIntelligence /></Page></Protected>} />
        <Route path="/cross-case" element={<Protected><Page><CrossCase /></Page></Protected>} />
        <Route path="/entities" element={<Protected><Page><EntityResolution /></Page></Protected>} />
        <Route path="/hypotheses" element={<Protected><Page><Hypotheses /></Page></Protected>} />
        <Route path="/information-gaps" element={<Protected><Page><InformationGaps /></Page></Protected>} />
        <Route path="/next-best-action" element={<Protected><Page><NextBestAction /></Page></Protected>} />
        <Route path="/audit" element={<Protected><Page><Audit /></Page></Protected>} />
        <Route path="/security" element={<Protected><Page><Security /></Page></Protected>} />
        <Route path="*" element={<Protected><Page>
          <div className="glass rounded-xl px-6 py-10 text-center">
            <p className="text-[15px] font-bold text-[var(--color-primary-deep)]">{t.common.routeNotFound}</p>
            <p className="mt-1 text-[13px] text-[var(--color-text-muted)]/80">{t.common.routeNotFoundBody}</p>
          </div>
        </Page></Protected>} />
      </Routes>
      <Toaster />
    </>
  )
}

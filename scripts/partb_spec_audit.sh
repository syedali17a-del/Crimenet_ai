#!/usr/bin/env bash
# Part B spec audit - every line below is a claim from the brief, checked against the source.
cd /home/user/frontend
pass=0; fail=0
ck(){ if eval "$2" >/dev/null 2>&1; then printf "  PASS  %s\n" "$1"; pass=$((pass+1)); else printf "  FAIL  %s\n" "$1"; fail=$((fail+1)); fi; }
say(){ printf "\n\033[1m%s\033[0m\n" "$1"; }

say "1. DESIGN TOKENS — defined once, in index.css"
for t in "--color-bg: #F4F7FC" "--color-surface: rgba(255, 255, 255, 0.65)" "--color-surface-solid: #FFFFFF" "--color-border: rgba(15, 42, 89, 0.10)" "--color-primary: #1450C4" "--color-primary-deep: #0B2F73" "--color-primary-soft: #E8F0FE" "--color-accent: #2FA7DB" "--color-success: #1E8E5A" "--color-warning: #B8791A" "--color-danger: #C4341F" "--color-text: #101828" "--color-text-muted: #5B6B85"; do
  ck "token $t" "grep -qF -- '$t' src/index.css"
done

say "2. GLASS SPEC — exact blur / border / radius / shadow"
ck "backdrop-filter: blur(16px) saturate(140%)" "grep -q 'blur(16px) saturate(140%)' src/index.css"
ck "-webkit-backdrop-filter present (Safari)" "grep -q 'webkit-backdrop-filter: blur(16px)' src/index.css"
ck "border-radius: 16px on panels" "grep -q 'radius-panel: 16px' src/index.css"
ck "shadow 0 8px 32px rgba(15,42,89,0.08)" "grep -q '0 8px 32px rgba(15, 42, 89, 0.08)' src/index.css"

say "3. GLASS PLACEMENT — allowed only where the brief allows it"
ck "graph canvas panel is SOLID (NetworkIntelligence)" "grep -q 'section className=\"surface-solid\"' src/pages/NetworkIntelligence.tsx"
ck "Dashboard KPI cards are glass" "grep -q 'export function KpiCard' src/components/shared/ui.tsx && grep -A 20 'export function KpiCard' src/components/shared/ui.tsx | grep -q glass"
ck "evidence provenance strip is glass" "sed -n '180,200p' src/pages/Evidence.tsx | grep -q glass"
ck "every <Card> in Security is solid" "[ -z \"\$(grep -n '<Card' src/pages/Security.tsx | grep -v 'solid')\" ]"
ck "every <Card> in Audit is solid" "[ -z \"\$(grep -n '<Card' src/pages/Audit.tsx | grep -v 'solid')\" ]"
ck "Security/Audit summary tiles are solid too" "[ -z \"\$(grep -n 'className=\"glass' src/pages/Security.tsx src/pages/Audit.tsx)\" ]"
ck "no GlassCard/glass used on any <table> wrapper" "! grep -rn 'glass' --include=*.tsx src/pages | grep -qi '<table'"

say "4. TYPOGRAPHY"
ck "page title 28px / 600 / primary-deep" "grep -q '.page-title { font-size: 28px; line-height: 1.2; font-weight: 600; color: var(--color-primary-deep); }' src/index.css"
ck "section header 16px / 600 / uppercase / 0.04em / muted" "grep -A 2 '.section-header {' src/index.css | grep -q 'font-size: 16px' && grep -A 3 '.section-header {' src/index.css | grep -q 'text-transform: uppercase' && grep -A 4 '.section-header {' src/index.css | grep -q 'letter-spacing: 0.04em'"
ck "body 14-15px / 1.5" "grep -q 'font-size: 14.5px' src/index.css && grep -q 'line-height: 1.5' src/index.css"
ck "tabular-nums for data" "grep -q '.data-num { font-variant-numeric: tabular-nums; }' src/index.css"
ck "monospace for hashes / evidence IDs" "grep -q 'font-family: var(--font-mono)' src/index.css"
ck "no second webfont / @import added" "! grep -qE '@import url|fonts.googleapis' src/index.css index.html"
ck "mono used on evidence ID and hash in Evidence page" "grep -q 'mono-id' src/pages/Evidence.tsx"

say "5. SPACING & LAYOUT"
ck "max content width 1400px" "grep -q 'max-w-\[1400px\]' src/components/layout/AppLayout.tsx"
ck "24px page padding (px-6)" "grep -q 'px-4 py-6 sm:px-6' src/components/layout/AppLayout.tsx"
ck "16px gap between cards (gap-4)" "grep -q 'gap-4' src/pages/Dashboard.tsx"
ck "left nav is fixed" "grep -q 'fixed bottom-0 left-0' src/components/layout/AppLayout.tsx"
ck "nav is glass" "grep -q 'glass fixed bottom-0 left-0' src/components/layout/AppLayout.tsx"
ck "nav scrolls independently" "grep -q 'overflow-y-auto' src/components/layout/AppLayout.tsx"

say "6. ELEVATION / INTERACTION"
ck "one hover lift: translateY(-2px) + shadow, 150ms" "grep -q 'translateY(-2px)' src/index.css && grep -q 'ease-hover: 150ms ease' src/index.css"
ck "2px focus ring, 2px offset, on every interactive element" "grep -q 'outline: 2px solid var(--color-primary); outline-offset: 2px;' src/index.css"

say "7. STATUS / CANDIDATE VISUAL LANGUAGE (the safety claim)"
ck "VERIFIED = solid success, filled" "grep -A 2 '.status-verified {' src/index.css | grep -q 'background: var(--color-success)'"
ck "CANDIDATE = outlined warning (transparent bg, never filled)" "grep -A 3 '.status-candidate {' src/index.css | grep -q 'background: transparent' && grep -A 4 '.status-candidate {' src/index.css | grep -q 'color: var(--color-warning)'"
ck "REJECTED = outlined dashed danger" "grep -A 3 '.status-rejected {' src/index.css | grep -q 'border: 1px dashed var(--color-danger)'"
ck "REJECTED claim text struck through" "grep -q '.status-rejected-claim { text-decoration: line-through' src/index.css"
ck "INSUFFICIENT = dashed muted" "grep -A 3 '.status-insufficient {' src/index.css | grep -q 'border: 1px dashed var(--color-text-muted)'"
ck "HIGH support is the filled badge" "sed -n '/function SupportBadge/,/^}/p' src/components/shared/ui.tsx | grep -q status-verified && sed -n '/function SupportBadge/,/^}/p' src/components/shared/ui.tsx | grep -q toUpperCase"
ck "MEDIUM/candidate tone is the outlined amber" "grep -q \"amber: 'bg-transparent text-\[var(--color-warning)\] ring-\[var(--color-warning)\]'\" src/components/shared/ui.tsx"
ck "candidate pill carries a clock icon, not a check" "sed -n '/function StatusPill/,/^}/p' src/components/shared/ui.tsx | grep -q 'clock'"

say "8. EMPTY / LOADING / ERROR STATES ON EVERY PAGE"
for p in Login Dashboard Cases CaseDetails Evidence EntityResolution CrossCase NetworkIntelligence MapIntelligence Timeline Hypotheses InformationGaps NextBestAction Security Audit Workflow LanguageSelect; do
  f="src/pages/$p.tsx"
  case "$p" in
    Login) ck "$p has a designed state (no data fetch)" "grep -qE 'EmptyState|role=\"alert\"|aria-live|Skeleton' $f" ;;
    LanguageSelect) ck "$p renders a static, always-populated list (no data fetch => no empty state possible)" "grep -q 'LANGS.map' $f" ;;
    Workflow) ck "$p has a designed empty state" "grep -qE 'EmptyState|border-dashed' $f" ;;
    *) ck "$p has empty + loading + error states" "grep -qE 'EmptyState|InsufficientEvidence|border-dashed' $f && grep -qE 'LoadingBlock|Skeleton' $f && grep -qE 'ErrorState' $f" ;;
  esac
done
ck "shimmer skeleton (not a spinner in a void)" "grep -q 'animation: shimmer' src/index.css"

say "9. PAGE-SPECIFIC NOTES"
ck "Login keeps the SYNTHETIC DEMONSTRATION DATA disclosure" "grep -q 'SYNTHETIC DEMONSTRATION DATA' src/pages/Login.tsx"
ck "Login keeps the demo-account disclosure" "grep -qi 'demo account\\|demo-account\\|INV-2201' src/pages/Login.tsx"
ck "Login has the faint network line pattern" "grep -qE 'grid-drift|net-|pattern' src/pages/Login.tsx"
ck "Security has dense tables in solid surfaces" "grep -q '<table' src/pages/Security.tsx && grep -q '<Card solid' src/pages/Security.tsx"
ck "Audit has dense tables in solid surfaces" "grep -q '<table' src/pages/Audit.tsx && grep -q '<Card solid' src/pages/Audit.tsx"
ck "NetworkIntelligence drawer shows the A2 explanation prominently" "grep -q 'Why this entity ranks here' src/components/graph/EntityPanel.tsx"

say "9b. FIXES MADE IN THIS PASS"
ck "Cases: case cards are solid, not glass (they carry body copy)" "! grep -q 'className=\"glass group flex flex-col' src/pages/Cases.tsx"
ck "Cases: a failed list fetch renders an error state with retry" "grep -q 'casesError && <ErrorState' src/pages/Cases.tsx"
ck "AppContext: casesError is part of the provider value" "grep -q 'casesError, activeCase' src/state/AppContext.tsx"
for p in CrossCase EntityResolution Hypotheses InformationGaps NextBestAction MapIntelligence Timeline; do
  ck "$p has a designed EmptyState" "grep -q '<EmptyState' src/pages/$p.tsx"
done

say "10. CONSTRAINTS"
ck "no new frontend dependencies added" "[ \"\$(python3 -c \"import json;print(len(json.load(open('package.json'))['dependencies']))\")\" -le 6 ]"
ck "safety copy: graph safety_note still rendered" "grep -q 'safety_note' src/components/graph/EntityPanel.tsx"
ck "safety copy: 'not evidence of leadership' wording preserved server-side" "grep -rq 'not evidence of leadership' ../backend/app"
ck "candidate-vs-verified copy present in UI" "grep -rq 'Candidate link' src/components/graph/EntityPanel.tsx"

printf "\n\033[1mPART B SPEC AUDIT: %s passed, %s failed\033[0m\n" "$pass" "$fail"

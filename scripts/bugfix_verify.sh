#!/usr/bin/env bash
# Verification for the four reproduced UI bugs. Every assertion is a fact about
# the shipped source (and, where marked, the shipped CSS bundle).
cd /home/user/frontend
pass=0; fail=0
ck(){ if eval "$2" >/dev/null 2>&1; then printf "  PASS  %s\n" "$1"; pass=$((pass+1)); else printf "  FAIL  %s\n" "$1"; fail=$((fail+1)); fi; }
say(){ printf "\n\033[1m%s\033[0m\n" "$1"; }
CSS=$(ls dist/assets/*.css | head -1)

say "BUG 1 — nav scrolls, and says so"
ck "aside is a flex column (was block)"        "grep -q 'hidden shrink-0 flex-col overflow-hidden' src/components/layout/AppLayout.tsx"
ck "aside clips its child (overflow-hidden)"   "grep -q 'flex-col overflow-hidden rounded-none' src/components/layout/AppLayout.tsx"
ck "aside is display:flex at lg (was block)"   "grep -q 'transition-\[width\] duration-200 lg:flex' src/components/layout/AppLayout.tsx"
ck "nav has a definite height (flex-1 min-h-0)" "grep -q 'flex min-h-0 flex-1 flex-col' src/components/layout/AppLayout.tsx"
ck "min-h-full is gone from the nav"           "! grep -q 'min-h-full flex-col gap-5 overflow-y-auto' src/components/layout/AppLayout.tsx"
ck "nav still scrolls + contains overscroll"   "grep -q 'overflow-y-auto overscroll-contain' src/components/layout/AppLayout.tsx"
ck "bottom fade exists and is decoration only" "grep -q 'pointer-events-none absolute inset-x-0 bottom-0 h-10' src/components/layout/AppLayout.tsx"
ck "fade is conditional on overflow AND not-at-end" "grep -q 'navHint.overflowing && !navHint.atEnd' src/components/layout/AppLayout.tsx"
ck "fade uses the panel surface token"         "grep -q 'rgba(255,255,255,0) 0%, var(--color-surface) 62%' src/components/layout/AppLayout.tsx"
ck "scroll-into-view is guarded (only when out of view)" "grep -q 'if (ir.bottom > cr.bottom - pad)' src/components/layout/AppLayout.tsx"
ck "scroll-into-view writes only the nav scrollTop" "grep -q 'el.scrollTop += (ir.bottom - cr.bottom) + pad' src/components/layout/AppLayout.tsx"
ck "it runs on route change"                   "grep -q '}, \[location.pathname, collapsed, syncNavHint\])' src/components/layout/AppLayout.tsx"
ck "active item is tracked by ref"             "grep -q 'activeNavRef : undefined' src/components/layout/AppLayout.tsx"
ck "NavLink forwards refs (react-router 7.18.3)" "grep -q 'React10.forwardRef' node_modules/react-router/dist/development/chunk-*.mjs"

say "BUG 2 — no text bleeds through any overlay"
ck ".glass-solid defined with 0.97 alpha"      "grep -q 'background: rgba(255, 255, 255, 0.97)' src/index.css"
ck ".glass-solid shipped in the built CSS"     "grep -q '.glass-solid' $CSS"
ck "built alpha is >=0.95 (f2..ff)"            "grep -q '.glass-solid{[^}]*#fffffff7' $CSS || grep -qE '.glass-solid\{[^}]*#fffffff[f2-9]' $CSS"
ck "search results dropdown -> glass-solid"    "grep -q 'glass-solid fade-in absolute left-0 right-0 top-\[calc(100%+6px)\]' src/components/layout/AppLayout.tsx"
ck "notification dropdown -> glass-solid"      "grep -q 'glass-solid absolute right-0 top-\[calc(100%+8px)\] z-50 w-\[320px\]' src/components/layout/AppLayout.tsx"
ck "profile dropdown -> glass-solid"           "grep -q 'glass-solid absolute right-0 top-\[calc(100%+8px)\] z-50 w-\[280px\]' src/components/layout/AppLayout.tsx"
ck "language listbox -> glass-solid"           "grep -q 'glass-solid absolute right-0 top-\[calc(100%+8px)\] z-50 w-\[212px\]' src/components/layout/LanguageSwitcher.tsx"
ck "NO absolute-positioned menu uses glass-strong any more" "! grep -rn 'glass-strong absolute' src --include=*.tsx"
ck "glass-strong kept for non-text-critical surfaces" "grep -q 'glass-strong' src/components/shared/ui.tsx"

say "BUG 3 — login language control is labelled"
ck "Login no longer passes compact"            "! grep -q '<LanguageSwitcher compact' src/pages/Login.tsx"
ck "Login renders the labelled switcher"       "grep -q '<LanguageSwitcher />' src/pages/Login.tsx"
ck "the label span renders when not compact"   "grep -q '{!compact && (' src/components/layout/LanguageSwitcher.tsx"

say "BUG 4 — checkbox row is independent of the field grid"
ck "verifiedOnly checkbox is outside the grid div" "python3 - <<'PY'
import re, pathlib
s = pathlib.Path('src/pages/NetworkIntelligence.tsx').read_text()
start = s.index('<div className=\"grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4\">')
# find the matching close of that grid div by brace/paren-free tag counting
depth = 0; i = start
while True:
    nxt_open = s.find('<div', i + 1); nxt_close = s.find('</div>', i + 1)
    if nxt_open != -1 and nxt_open < nxt_close:
        depth += 1; i = nxt_open
    else:
        if depth == 0:
            grid_end = nxt_close; break
        depth -= 1; i = nxt_close
grid = s[start:grid_end]
assert 'verifiedOnly' not in grid, 'checkbox still inside the grid'
assert grid.count('<TextInput') == 3 and grid.count('<Select') == 1
PY"
ck "two date inputs own their own grid cells"  "python3 -c \"
import pathlib
s = pathlib.Path('src/pages/NetworkIntelligence.tsx').read_text()
g = s[s.index('grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4'):s.index('BUG 4: structurally independent')]
assert g.count('type=\\\"date\\\"') == 2, 'date inputs missing'
assert 'flex items-center gap-2' not in g, 'dates are still nested in one cell'
\""
ck "checkbox sits in its own full-width row"   "grep -q 'BUG 4: structurally independent of the field grid' src/pages/NetworkIntelligence.tsx"
ck "checkbox row uses w-fit (label does not stretch/clip)" "grep -q 'flex w-fit items-center gap-2 text-\[12.5px\] font-semibold' src/pages/NetworkIntelligence.tsx"

printf "\n\033[1mBUGFIX VERIFICATION: %s passed, %s failed\033[0m\n" "$pass" "$fail"

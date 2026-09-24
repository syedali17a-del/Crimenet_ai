# CrimeNet AI — Multilingual Implementation (English / தமிழ் / हिन्दी)

**Status: core application multilingual and building clean.** 4 files remain to convert
(listed in §8). Nothing was rewritten that already worked — every page kept its layout,
logic and API calls; only its literals moved into the dictionary.

---

## 1. Audit finding (before any change)

```
grep -RIn "i18n|useTranslation|LanguageContext|translations|locale" frontend/src → 0 matches
```

There was **no internationalisation layer of any kind**. All 6,904 lines of frontend code
were hardcoded English. A regex extractor over all 33 source files found **~796 distinct
user-facing strings**. So the task was not to fix i18n — it was to build it.

## 2. Architecture (no new dependencies)

Per your stack constraint, **no i18next / react-intl / FormatJS**. The layer is hand-rolled
TypeScript + React context — zero runtime dependencies added.

```
src/i18n/
  tri.ts                  Lang = 'en'|'ta'|'hi', Tri<T>, LANGUAGE_META (endonym, locale, script)
  index.ts                buildDict/dictFor cache · humanise() · lookup() · makeFormatters()
                          · resolveStatus() · resolveInsufficient()
  LanguageContext.tsx     LanguageProvider + useI18n() → { lang, chosen, setLang, chooseLang,
                          t, fmt, meta, tok }
  strings/
    common.ts             cross-cutting vocabulary, principles, classification banner
    tokens.ts             backend-token → label maps (19 vocabularies)
    nav.ts                sidebar groups, 14 nav items, search, notifications, profile
    auth.ts               language-select screen + full login copy
    boot.ts               boot splash steps and handshake failure
    pages.ts              title / eyebrow / description for all 15 pages
    dashboard.ts          command centre
    cases.ts              case list + case file
    evidence.ts           evidence registry + document intelligence + upload modal
    analysis.ts           entity resolution · cross-case · network · timeline
    reasoning.ts          hypotheses · information gaps · next-best action · agent modal
```

**Key design decision — missing keys are a compile error, not a runtime fallback.**
Each dictionary file declares `const en = {...}`, then `type Shape = typeof en`, then
`const ta: Shape = {...}` and `const hi: Shape = {...}`. If a Tamil or Hindi key is missing
or misspelled, `tsc` fails the build. That is how the "no missing translation keys"
requirement is *enforced* rather than merely intended.

Access is by object path (`t.evidence.registeredHash`), never runtime string lookup, so
autocomplete works and typos cannot reach production.

## 3. Language selection before login

`main.tsx` now wraps everything:

```
StrictMode → BrowserRouter → LanguageProvider → AppProvider → App
```

`App.tsx` gates on `chosen`:

```
BootSplash  →  LanguageSelect (if no language chosen yet)  →  Login  →  Console
```

`pages/LanguageSelect.tsx` shows three cards — **each labelled in its own script**
(English / தமிழ் / हिन्दी), hovering a card live-previews that language, and Continue
proceeds to login. The choice persists in `crimenet.lang` + `crimenet.lang.chosen`.

## 4. Switcher available everywhere

`components/layout/LanguageSwitcher.tsx` — a globe dropdown showing the **current**
language, mounted in:

* the authenticated top bar (`AppLayout`), and
* the login page header (compact variant), so language can be changed before signing in.

Switching calls `setLang` only. It does **not** log out, does **not** reload, and does
**not** refetch: React re-renders from context, so the active case, current route,
selected graph node, filters, and any analysis result on screen all survive the switch.

## 5. What is never translated

Identifiers pass through verbatim in all three languages, by design:

`CASE-101` · `EV-1024` · `PER-001` · `TN01AB1234` · `+919840012345` · SHA-256 digests ·
ledger block hashes · `RapidFuzz` · `Louvain` · `Isolation Forest` · `SHA-256` · `JWT` ·
`RBAC` · `OCR` · `NER` · API endpoints and HTTP methods.

Formatters (`fmt.date`, `fmt.dateTime`, `fmt.number`, `fmt.percent`, `fmt.list`) are bound
to `en-IN` / `ta-IN` / `hi-IN` via `Intl` and are used only for dates, times and counts —
never for identifiers.

## 6. Backend tokens, not backend translations

**No analytical logic changed.** The backend keeps emitting structured tokens; the frontend
maps them. 19 vocabularies are covered, including all 33 audit actions, 8 relationship
types, entity types, evidence types, processing / integrity / verification statuses, case
statuses, priorities, agents and lead statuses.

Two safety valves:

* `humanise()` — an unknown token degrades to readable text
  (`RELATIONSHIPS_CANDIDATE` → "Relationships candidate") instead of rendering a raw key.
* `resolveStatus()` — a status string is tried against every status vocabulary in turn,
  so one `<StatusBadge>` component localises verification, integrity, processing,
  case-state and corroboration verdicts alike.

Because `SupportBadge` / `StatusBadge` / `EntityChip` / `InsufficientEvidence` /
`ErrorState` / `LoadingBlock` / `Principle` / `ClassificationTag` live in the shared UI kit,
localising those eight components localised hundreds of call sites across every page at once.

## 7. Script-aware typography

Appended to `index.css`, keyed off the `lang-ta` / `lang-hi` class the provider puts on
`<html>` (it also sets `documentElement.lang` and `data-script`):

* Tamil: `'Noto Sans Tamil', 'Nirmala UI', 'Latha', 'Tamil Sangam MN'`
* Devanagari: `'Noto Sans Devanagari', 'Nirmala UI', 'Mangal', 'Kohinoor Devanagari'`
* line-height raised to 1.6–1.65 so matras and vowel signs are never clipped
* Latin `tracking-*` and `uppercase` utilities neutralised for Indic text (they break
  conjuncts and mean nothing in these scripts)
* `overflow-wrap: anywhere` and auto-height buttons so longer Indic labels grow the
  control instead of overflowing it

System font stacks only — **no Google Fonts request**, which matters because the preview
iframe has no network access.

## 8. Coverage measured, not claimed

`tools/i18n_scan.py` re-scans the source for user-facing literals:

```
 residual  file
       55  pages/Security.tsx
       48  pages/Audit.tsx
       22  components/graph/EntityPanel.tsx
       20  pages/MapIntelligence.tsx
        9  pages/Workflow.tsx
       11  (7 files with 1–3 incidental strings)
------------------------------------------------
      166  TOTAL   (was 796 — 79% converted)
```

**Fully converted (compile-verified):** boot splash · language select · login · app shell
(sidebar, search, notifications, profile, case context) · shared UI kit · Dashboard ·
Cases · Case Details · Evidence · Entity Resolution · Cross-Case · Network Intelligence ·
Timeline · Hypotheses · Information Gaps · Next-Best Action · Agent Run Modal · all 15
page headers.

**Still English:** Settings/Security, Audit & Evidence Integrity, the graph Entity Panel,
Map Intelligence, and the Workflow runner's step labels. These are the next four files.

## 9. Honest limitation: agent-generated prose

Findings text, gap statements and next-best-action rationales are **composed sentences
generated by the reasoning agents at runtime** (e.g. *"Potential cross-case association
CASE-101 ↔ CASE-202"*, *"Name similarity: Ravi Kumar ↔ R. Kumar (86.0%)"*). Their
surrounding labels, statuses and badges are translated; the generated sentences themselves
remain English in this build.

Translating them properly requires the backend to emit `{template_id, params}` instead of a
finished sentence — an *additive* change that does not touch analytical logic. That is the
correct next phase; faking it client-side with string matching would be fragile and would
silently mistranslate evidence descriptions, which is not acceptable in an evidence system.

`INSUFFICIENT EVIDENCE: <reason>` is already handled: `resolveInsufficient()` strips the
prefix, localises it, looks the reason up in `tokens.insufficientReason`, and falls back to
the original sentence when the reason is not a known token — never dropping information.

## 10. Spec correction

The brief gave Hindi "Evidence" as `साक्षियम्`, which is a Sanskrit/Tamil-style form. The
standard Hindi term is **`साक्ष्य`**, which is what the Hindi dictionary uses throughout.

## 11. Verification performed

| Check | Result |
|---|---|
| `npx tsc -b --force` | exit 0, no errors |
| `npm run build` | clean — 1,265 kB JS (357 kB gzip), 90 kB CSS |
| Bundle cost of 3 full dictionaries | +204 kB raw / +43 kB gzip over baseline |
| Missing `ta`/`hi` keys | structurally impossible — compile error |
| Backend | untouched; uvicorn healthy, `/api/health` OK |
| Dev server | Vite running, HMR clean through every conversion |

**Not verified:** rendered screenshots. This sandbox has no browser binary and no
Playwright, so "inspect every rendered page visually" could not be done here. Verification
was source review + type checking + production build + the coverage scanner. Please open
the live preview and switch languages to confirm the visual result.

---

*All data remains SYNTHETIC DEMONSTRATION DATA in every language.*

# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A Next.js 16 application using the App Router, React 19 and next-intl (English at `/`, Dutch at `/nl`). `bun` for install, Biome for lint + format, Vitest for tests. Turbopack runs the dev server.

## Mental model

```
src/
├── app/
│   ├── [locale]/
│   │   ├── layout.tsx  # root layout: <html lang>, metadata, NextIntlClientProvider
│   │   └── page.tsx    # home page (server component by default), hreflang alternates
│   └── globals.css     # global styles
├── components/
│   └── LanguageSwitcher.tsx  # client component: links to the current page in each locale
├── i18n/
│   ├── routing.ts      # locales, default locale, `as-needed` URL prefix
│   ├── request.ts      # loads messages/<locale>.json for each request
│   └── navigation.ts   # locale-aware Link, redirect, usePathname, useRouter, getPathname
└── proxy.ts            # next-intl middleware: locale detection and redirects
messages/
├── en.json             # base strings and fallback
└── nl.json             # Dutch, same keys and placeholders
next.config.ts          # Next.js config, wrapped with the next-intl plugin
vitest.config.ts        # Vitest config
package.json            # type: module, scripts, dependencies
tsconfig.json           # strict mode, `@/*` → src/*
biome.json              # lint + format rules
```

The runtime path is `request → src/proxy.ts (picks the locale) → src/app/[locale]/<segment>/page.tsx → server-rendered HTML → hydration where `"use client"` is declared`. Layouts wrap nested segments; `loading.tsx` / `error.tsx` are framework-reserved.

## Invariants

- App Router only (`src/app/`); do not introduce a `pages/` directory.
- Pages and layouts live under `src/app/[locale]/`. Never add `src/app/layout.tsx`: it would become the root layout and `next/root-params` would stop resolving `[locale]`.
- Import `Link`, `redirect`, `usePathname` and `useRouter` from `@/i18n/navigation`, not `next/link` / `next/navigation`, so URLs keep the right locale prefix.
- User-facing text is multilingual: `en` (base, fallback) and `nl` (informal je/jij). Never hardcode user-visible strings; add each key to every language file in the same change. Logs and developer errors stay English.
- Server Components are the default; opt into client with `"use client"` at the top of the file, and only for components that need it.
- Path alias `@/` maps to `src/` — use it consistently.
- Strict TypeScript — no `// @ts-ignore`, no `any` without justification.
- Biome is the only linter / formatter — do not add ESLint or Prettier configs.
- Functions / components stay small (5–10 lines target, 20 max).
- Errors surface at the boundary; use `error.tsx` for render-time recovery.
- GSAP is the animation tool (`gsap` + `@gsap/react` ship by default) — don't add framer-motion or other animation libraries.
- `bun` owns the lockfile. Add deps with `bun add <pkg>`.
- The social preview lives in `public/og.html`. Its four base classes — `.og-canvas`, `.og-brand`, `.og-title`, `.og-subtitle` — are fixed: restyle them and the `:root` tokens (font, colors, sizes, layout) and replace the placeholder copy, but never rename or drop them. Screenshot `.og-canvas` at 1200x630 into `public/og.png`.

## Common change patterns

- **Add a route** → new folder under `src/app/[locale]/` with `page.tsx`; copy the home page's `generateMetadata` with the route's own `href` for hreflang alternates.
- **Add an animation** → `"use client"` component with `useGSAP()` from `@gsap/react`; register plugins like `ScrollTrigger` once at module top.
- **Add a layout** → `layout.tsx` next to the routes it wraps.
- **Add a server action** → exported `async function` with `"use server"`, called from a client component. `next/root-params` does not resolve in Server Actions or Route Handlers, so translate there with `getTranslations({ locale, namespace })`.
- **Add an API route** → `route.ts` with `GET` / `POST` / etc. exports.
- **Add a dependency** → `bun add <pkg>` (or `bun add -d <pkg>` for dev).
- **Add or change text** → edit `messages/en.json` and `messages/nl.json`, call `useTranslations('<Namespace>')` (or `await getTranslations('<Namespace>')` in async server code), run `just i18n-check`. Plurals are `{ "one", "other" }` objects picked with `Intl.PluralRules`, as on the home page.
- **Add a language** → add `messages/<locale>.json` (+ register in `locales` in `src/i18n/routing.ts`), run `just i18n-check`.

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `i18n-check` + `lint` + `typecheck` + `test`

Recipe reference:

- `just install` — `bun install`
- `just dev` — Next.js dev server with Turbopack (agent must not run this)
- `just preview` — `next start` against the production build
- `just lint` / `just lint-fix` — Biome check / `--write`
- `just typecheck` — `tsc --noEmit`
- `just test` — Vitest
- `just build` — production build
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just i18n-check` — every language file has the base's keys and placeholders
- `just og-check` — warns while `public/og.png` is missing (never fails)
- `just just-fmt-check` — verify Justfile formatting
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds and the i18n language files (single source of truth)
- As this project grows, add nested `CLAUDE.md` files in high-value subfolders (`src/app/[locale]/<section>/`, `src/components/`, `src/lib/`, integrations) following the `claude-md-tree` skill's context-packet pattern.

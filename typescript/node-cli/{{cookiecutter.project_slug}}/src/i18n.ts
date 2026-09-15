/**
 * Zero-dependency i18n. `locales/en.json` holds the source strings and is the fallback.
 *
 * Keys are dotted (`hello.greeting`), placeholders are single braces (`{name}`), and plurals are
 * `{ "one": …, "other": … }` objects chosen by `params.count` with `Intl.PluralRules`.
 * Add a language: create `locales/<locale>.json`, import it below and add it to `catalogs`.
 */
import en from './locales/en.json' with { type: 'json' }
import nl from './locales/nl.json' with { type: 'json' }

type Messages = { [key: string]: string | Messages }
export type Params = Record<string, string | number>

export const BASE_LOCALE = 'en'
const catalogs: Record<string, Messages> = { en, nl }
export const LOCALES = Object.keys(catalogs)

/** Translate `key` into `locale`, falling back to the base locale, then to the key itself. */
export function t(locale: string, key: string, params: Params = {}): string {
  const text = resolve(locale, key, params.count) ?? resolve(BASE_LOCALE, key, params.count)
  return (text ?? key).replace(/\{(\w+)\}/g, (match, name: string) => String(params[name] ?? match))
}

function resolve(locale: string, key: string, count?: string | number): string | undefined {
  const entry = key
    .split('.')
    .reduce<string | Messages | undefined>(
      (node, part) =>
        typeof node === 'object' && Object.hasOwn(node, part) ? node[part] : undefined,
      catalogs[locale],
    )
  if (typeof entry !== 'object') return entry
  const form = entry[new Intl.PluralRules(locale).select(Number(count))] ?? entry.other
  return typeof form === 'string' ? form : undefined
}

/** `nl_NL.UTF-8` → `nl`. Returns undefined for `C`, `POSIX` and unsupported locales. */
export function normalize(tag: string | undefined): string | undefined {
  // ponytail: matches the language subtag only; add region matching with the first regional locale (pt-BR)
  const language = tag
    ?.trim()
    .split(/[-_.@]/)[0]
    .toLowerCase()
  return LOCALES.find((locale) => locale === language)
}

/** Best supported locale from an `Accept-Language` header, by q-value; `en` when none match. */
export function negotiate(acceptLanguage: string | undefined): string {
  const ranges = (acceptLanguage ?? '').split(',').map((range) => ({
    locale: normalize(range.split(';')[0]),
    q: Number(/;\s*q=([\d.]+)/.exec(range)?.[1] ?? 1),
  }))
  const best = ranges.filter((range) => range.locale && range.q > 0).sort((a, b) => b.q - a.q)[0]
  return best?.locale ?? BASE_LOCALE
}

/** CLI locale from the first set of `LC_ALL`, `LC_MESSAGES`, `LANG`; `en` when unsupported. */
export function localeFromEnv(env: Record<string, string | undefined> = process.env): string {
  return normalize(env.LC_ALL || env.LC_MESSAGES || env.LANG) ?? BASE_LOCALE
}

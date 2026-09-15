import { type Locale, localizeHref } from '$lib/paraglide/runtime'

/** Localized href without the trailing slash: `/nl/` would 308-redirect to `/nl`. */
export function localizePath(pathname: string, locale: Locale): string {
  return localizeHref(pathname, { locale }).replace(/(.)\/$/, '$1')
}

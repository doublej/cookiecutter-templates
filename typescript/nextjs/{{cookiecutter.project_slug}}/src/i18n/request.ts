import { notFound } from 'next/navigation'
import * as rootParams from 'next/root-params'
import { hasLocale } from 'next-intl'
import { getRequestConfig } from 'next-intl/server'
import { routing } from './routing'

export default getRequestConfig(async ({ locale }) => {
  // An explicit locale (Server Actions, Route Handlers) wins; otherwise read the [locale] root param.
  let resolved = locale
  if (!resolved) {
    const param = await rootParams.locale()
    if (!hasLocale(routing.locales, param)) notFound()
    resolved = param
  }
  return {
    locale: resolved,
    messages: (await import(`../../messages/${resolved}.json`)).default,
  }
})

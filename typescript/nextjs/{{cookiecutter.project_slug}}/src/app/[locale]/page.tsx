import type { Metadata } from 'next'
import { useLocale, useTranslations } from 'next-intl'
import { getLocale } from 'next-intl/server'
import LanguageSwitcher from '@/components/LanguageSwitcher'
import { getPathname } from '@/i18n/navigation'
import { routing } from '@/i18n/routing'

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale()
  const href = '/'
  const languages = Object.fromEntries(
    routing.locales.map((l) => [l, getPathname({ href, locale: l })]),
  )
  return {
    alternates: {
      canonical: getPathname({ href, locale }),
      languages: {
        ...languages,
        'x-default': getPathname({ href, locale: routing.defaultLocale }),
      },
    },
  }
}

export default function Home() {
  const t = useTranslations('Home')
  const locale = useLocale()
  const count = routing.locales.length
  return (
    <main>
      <h1>{t('title')}</h1>
      <p>{t('intro', { file: `messages/${locale}.json` })}</p>
      {/* Plurals are { one, other } objects; Intl.PluralRules picks the form. */}
      <p>{t(`languages.${new Intl.PluralRules(locale).select(count)}`, { count })}</p>
      <LanguageSwitcher />
    </main>
  )
}

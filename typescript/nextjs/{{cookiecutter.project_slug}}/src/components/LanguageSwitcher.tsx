'use client'

import { useLocale, useTranslations } from 'next-intl'
import { Link, usePathname } from '@/i18n/navigation'
import { routing } from '@/i18n/routing'

export default function LanguageSwitcher() {
  const t = useTranslations('LanguageSwitcher')
  const locale = useLocale()
  const pathname = usePathname()
  return (
    <nav aria-label={t('label')}>
      {routing.locales.map((l) => (
        <Link key={l} href={pathname} locale={l} aria-current={l === locale ? 'page' : undefined}>
          {l.toUpperCase()}
        </Link>
      ))}
    </nav>
  )
}

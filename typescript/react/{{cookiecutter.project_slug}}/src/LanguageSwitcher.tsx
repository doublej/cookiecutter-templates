import { m } from './paraglide/messages'
import { getLocale, locales, setLocale } from './paraglide/runtime'

// setLocale stores the choice in localStorage and reloads the page, so no React state is needed.
export default function LanguageSwitcher() {
  return (
    <nav aria-label={m.language()}>
      {locales.map((locale) => (
        <button
          key={locale}
          type="button"
          aria-pressed={locale === getLocale()}
          onClick={() => setLocale(locale)}
        >
          {locale}
        </button>
      ))}
    </nav>
  )
}

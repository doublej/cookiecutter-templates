import { describe, expect, it } from 'vitest'
import { LOCALES, localeFromEnv, negotiate, normalize, t } from './i18n.js'

describe('i18n', () => {
  it('derives the supported locales from the language files', () => {
    expect(LOCALES).toEqual(['en', 'nl'])
  })

  it('normalizes POSIX and BCP 47 tags, rejecting C, POSIX and unsupported locales', () => {
    expect(normalize('nl_NL.UTF-8')).toBe('nl')
    expect(normalize('nl-BE')).toBe('nl')
    expect(normalize('C')).toBeUndefined()
    expect(normalize('POSIX')).toBeUndefined()
    expect(normalize('fr_FR')).toBeUndefined()
  })

  it('negotiates Accept-Language by q-value', () => {
    expect(negotiate('fr-FR, nl;q=0.8, en;q=0.5')).toBe('nl')
    expect(negotiate('en;q=0.4, nl-NL;q=0.9')).toBe('nl')
    expect(negotiate('nl;q=0, fr')).toBe('en')
    expect(negotiate(undefined)).toBe('en')
  })

  it('reads LC_ALL, then LC_MESSAGES, then LANG', () => {
    expect(localeFromEnv({ LC_ALL: 'nl_NL.UTF-8', LANG: 'en_US.UTF-8' })).toBe('nl')
    expect(localeFromEnv({ LC_ALL: '', LC_MESSAGES: 'nl_NL', LANG: 'en_US' })).toBe('nl')
    expect(localeFromEnv({ LANG: 'C' })).toBe('en')
    expect(localeFromEnv({})).toBe('en')
  })

  it('fills placeholders', () => {
    expect(t('nl', 'hello.greeting', { name: 'Mars' })).toBe('Hallo, Mars!')
  })

  it('picks the plural form for the locale', () => {
    expect(t('en', 'hello.done', { count: 1 })).toBe('Greeted 1 person')
    expect(t('nl', 'hello.done', { count: 3 })).toBe('3 mensen begroet')
  })

  it('falls back to en, then to the key', () => {
    expect(t('fr', 'hello.greeting', { name: 'Mars' })).toBe('Hello, Mars!')
    expect(t('nl', 'missing.key')).toBe('missing.key')
  })
})

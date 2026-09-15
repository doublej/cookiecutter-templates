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
    expect(t('nl', 'hello', { name: 'Mars' })).toBe('Hallo vanuit Mars!')
  })

  it('picks the plural form for the locale', () => {
    expect(t('en', 'uptime', { count: 1 })).toBe('Running for 1 second')
    expect(t('nl', 'uptime', { count: 2 })).toBe('Draait al 2 seconden')
  })

  it('falls back to en, then to the key', () => {
    expect(t('fr', 'hello', { name: 'Mars' })).toBe('Hello from Mars!')
    expect(t('nl', 'missing.key')).toBe('missing.key')
  })
})

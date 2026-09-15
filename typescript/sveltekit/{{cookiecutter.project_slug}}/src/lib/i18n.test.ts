import { describe, expect, it } from 'vitest'
import { localizePath } from './i18n'

describe('localizePath', () => {
  it('drops the trailing slash that would redirect', () => {
    expect(localizePath('/', 'nl')).toBe('/nl')
  })

  it('leaves other paths as Paraglide localizes them', () => {
    expect(localizePath('/', 'en')).toBe('/')
    expect(localizePath('/about', 'nl')).toBe('/nl/about')
    expect(localizePath('/nl/about', 'en')).toBe('/about')
  })
})

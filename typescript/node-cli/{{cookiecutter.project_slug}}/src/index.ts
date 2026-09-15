import { BASE_LOCALE, t } from './i18n.js'

export const name = '{{ cookiecutter.project_name }}'
export const version = '0.1.0'

export function greet(name: string, locale = BASE_LOCALE): string {
  return t(locale, 'hello.greeting', { name })
}

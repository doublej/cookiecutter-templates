{%- set chrome = {"6.0": "chrome76", "7.0": "chrome94", "8.0": "chrome108"}[cookiecutter.tizen_required_version] -%}
import { paraglideVitePlugin } from '@inlang/paraglide-js'
import { sveltekit } from '@sveltejs/kit/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    sveltekit(),
    // Keep outdir and strategy in sync with the `prepare` script in package.json. The TV follows
    // the system language. Never add urlPatterns or routeStrategies: they pull in a URLPattern
    // polyfill, and Chromium 76 (Tizen 6.0) has no URLPattern.
    paraglideVitePlugin({
      project: './project.inlang',
      outdir: './src/lib/paraglide',
      strategy: ['localStorage', 'preferredLanguage', 'baseLocale'],
    }),
  ],
  // Tizen {{ cookiecutter.tizen_required_version }} ships an old Chromium — bump this
  // together with tizen_required_version in config.xml, never separately.
  build: { target: '{{ chrome }}' },
})

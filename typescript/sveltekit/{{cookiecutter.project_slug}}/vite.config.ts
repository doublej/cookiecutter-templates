import { paraglideVitePlugin } from '@inlang/paraglide-js'
import { sveltekit } from '@sveltejs/kit/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    sveltekit(),
    // Keep outdir and strategy in sync with the `prepare` script in package.json.
    // The URL decides the language: `/` stays English even for a Dutch browser.
    paraglideVitePlugin({
      project: './project.inlang',
      outdir: './src/lib/paraglide',
      strategy: ['url', 'cookie', 'preferredLanguage', 'baseLocale'],
    }),
  ],
})

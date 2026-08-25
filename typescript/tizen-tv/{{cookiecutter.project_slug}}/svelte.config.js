import adapter from '@sveltejs/adapter-static'
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte'

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    // A .wgt is served from the TV's local filesystem: everything must be
    // prerendered and every asset URL relative — no server, no absolute /paths.
    // Don't add `fallback` here: a fallback page is written with absolute
    // /_app/ URLs, which 404 on-device.
    adapter: adapter({ precompress: false }),
    paths: { relative: true },
  },
}

export default config

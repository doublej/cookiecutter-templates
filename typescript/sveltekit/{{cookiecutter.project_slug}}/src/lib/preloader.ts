/**
 * Lifts the preloader from app.html once the page is hydrated, window `load` has fired and the
 * fonts it uses are in. Call from the root layout's onMount: in dev, SvelteKit swaps its inlined
 * CSS for Vite's copy just before hydrating, which re-requests every font, so waiting for `load`
 * alone reveals the page in the fallback font.
 */
export async function revealWhenReady(): Promise<void> {
  if (document.readyState !== 'complete') {
    await new Promise((resolve) => addEventListener('load', resolve, { once: true }))
  }
  document.body.getBoundingClientRect() // lay out now so the fonts this page uses start loading
  await document.fonts.ready
  document.documentElement.classList.remove('preloading')
}

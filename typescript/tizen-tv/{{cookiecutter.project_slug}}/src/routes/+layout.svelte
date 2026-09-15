<script lang="ts">
import { onMount } from 'svelte'
import { getLocale } from '$lib/paraglide/runtime'
import { initRemote } from '$lib/remote'

const { children } = $props()

onMount(() => {
  // ssr=false: the prerendered shell keeps app.html's lang, so set it once the locale is known.
  document.documentElement.lang = getLocale()
  return initRemote()
})
</script>

{@render children()}

<style>
  :global(html),
  :global(body) {
    width: 1920px;
    height: 1080px;
    margin: 0;
    overflow: hidden;
    background: #0b0b0f;
    color: #f5f5f7;
    font-family: system-ui, sans-serif;
  }

  /* TV overscan: keep anything meaningful inside the 5% safe area. */
  :global(body) {
    padding: 54px 96px;
    box-sizing: border-box;
  }
</style>

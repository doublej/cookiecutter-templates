<script lang="ts">
import { onMount } from 'svelte'
import { initRemote } from '$lib/remote'

const { children } = $props()

onMount(() => initRemote())
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

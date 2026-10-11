<script lang="ts">
import { onMount } from 'svelte'
import { page } from '$app/state'
import { localizePath } from '$lib/i18n'
import LanguageSwitcher from '$lib/LanguageSwitcher.svelte'
import { locales } from '$lib/paraglide/runtime'
import { revealWhenReady } from '$lib/preloader'

const { children } = $props()

onMount(revealWhenReady)
</script>

<svelte:head>
  {#each locales as locale (locale)}
    <link rel="alternate" hreflang={locale} href={localizePath(page.url.pathname, locale)} />
  {/each}
</svelte:head>

<LanguageSwitcher />

{@render children()}

<script lang="ts">
import { page } from '$app/state'
import { localizePath } from '$lib/i18n'
import { m } from '$lib/paraglide/messages'
import { getLocale, locales } from '$lib/paraglide/runtime'
</script>

<!-- Full reload: m.*() is not reactive, so a client-side nav would keep the old language. -->
<nav aria-label={m.language()}>
  {#each locales as locale (locale)}
    <a
      href={localizePath(page.url.pathname, locale)}
      hreflang={locale}
      aria-current={locale === getLocale() ? 'true' : undefined}
      data-sveltekit-reload>{locale}</a
    >
  {/each}
</nav>

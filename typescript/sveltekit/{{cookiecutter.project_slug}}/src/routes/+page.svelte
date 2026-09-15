<script lang="ts">
import { m } from '$lib/paraglide/messages'
</script>

<h1>{{ cookiecutter.project_name }}</h1>
<p>{m.intro()}</p>
<p>{m.greeting({ name: 'JJ' })}</p>

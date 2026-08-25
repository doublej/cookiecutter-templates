<h1>{{ cookiecutter.project_name }}</h1>
<p>{{ cookiecutter.description }}</p>

<div class="row">
  <button class="tile" type="button" data-focusable>One</button>
  <button class="tile" type="button" data-focusable>Two</button>
  <button class="tile" type="button" data-focusable>Three</button>
</div>

<p class="hint">Arrow keys move focus, Enter selects, Back exits.</p>

<style>
  h1 {
    font-size: 64px;
    margin: 0 0 8px;
  }

  p {
    font-size: 28px;
    color: #a0a0ab;
  }

  .row {
    display: flex;
    gap: 32px;
    margin-top: 64px;
  }

  .tile {
    width: 360px;
    height: 240px;
    border: 4px solid transparent;
    border-radius: 16px;
    background: #1c1c24;
    color: inherit;
    font-size: 32px;
    transition: transform 0.15s ease;
  }

  .tile:focus {
    border-color: #4c8dff;
    outline: none;
    transform: scale(1.06);
  }

  .hint {
    margin-top: 64px;
    font-size: 22px;
  }
</style>

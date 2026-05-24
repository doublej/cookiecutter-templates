# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

## Requirements

- [Bun](https://bun.sh/)

## Getting Started

```bash
bun install
bun run dev
```

## Common Commands

| Command | Description |
|---------|-------------|
| `bun install` | Install dependencies |
| `bun run dev` | Run package entry with watch |
| `bun run build` | Build TypeScript declarations |
| `bun run test` | Run tests |
| `bun run lint` | Lint with Biome |

## Project Structure

```
src/
  index.ts       # Package exports
  index.test.ts  # Bun tests
```

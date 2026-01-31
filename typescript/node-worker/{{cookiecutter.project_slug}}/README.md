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
| `bun run dev` | Start with watch |
| `bun run build` | Build for production |
| `bun run start` | Start worker |
| `bun run test` | Run tests |
| `bun run lint` | Lint with Biome |

## Project Structure

```
src/
  index.ts       # Worker entry point
  env.ts         # Environment validation
  logger.ts      # Pino logger
```

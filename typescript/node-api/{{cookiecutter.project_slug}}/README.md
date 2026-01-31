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
| `bun run dev` | Start dev server with watch |
| `bun run build` | Build for production |
| `bun run start` | Start production server |
| `bun run test` | Run tests |
| `bun run lint` | Lint with Biome |

## Project Structure

```
src/
  index.ts       # Elysia API server
  env.ts         # Environment validation
  logger.ts      # Pino logger
```

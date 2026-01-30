{% if cookiecutter.project_type == 'cli' %}
export const name = '{{ cookiecutter.project_name }}'
export const version = '0.1.0'

export function greet(name: string): string {
  return `Hello, ${name}!`
}
{% elif cookiecutter.project_type == 'api' %}
import { Elysia } from 'elysia'
import { cors } from '@elysiajs/cors'
import { swagger } from '@elysiajs/swagger'
import { env } from './env.js'
import { logger } from './logger.js'

const app = new Elysia()
  .use(cors())
  .use(swagger())
  .get('/health', () => ({ status: 'ok', timestamp: new Date().toISOString() }))
  .get('/', () => ({ message: 'Hello from {{ cookiecutter.project_name }}!' }))
  .listen({ port: env.PORT, hostname: env.HOST })

logger.info(`Server running at http://${env.HOST}:${env.PORT}`)

export { app }
{% elif cookiecutter.project_type == 'library' %}
export function greet(name: string): string {
  return `Hello, ${name}!`
}

export function add(a: number, b: number): number {
  return a + b
}
{% elif cookiecutter.project_type == 'worker' %}
import { env } from './env.js'
import { logger } from './logger.js'

{% if cookiecutter.worker_type == 'simple' %}
async function main() {
  logger.info('Worker starting')
  // Your worker logic here
  logger.info('Worker completed')
}

main().catch((err) => {
  logger.error(err, 'Worker failed')
  process.exit(1)
})
{% elif cookiecutter.worker_type == 'cron' %}
const INTERVAL_MS = 60_000

async function tick() {
  logger.info('Tick')
  // Your scheduled logic here
}

async function main() {
  logger.info('Worker starting')
  await tick()
  setInterval(tick, INTERVAL_MS)
}

main().catch((err) => {
  logger.error(err, 'Worker failed')
  process.exit(1)
})
{% else %}
async function main() {
  logger.info('Worker starting')

  process.on('SIGTERM', () => {
    logger.info('Received SIGTERM, shutting down')
    process.exit(0)
  })

  // Your long-running logic here
  await new Promise(() => {}) // Keep alive
}

main().catch((err) => {
  logger.error(err, 'Worker failed')
  process.exit(1)
})
{% endif %}
{% endif %}

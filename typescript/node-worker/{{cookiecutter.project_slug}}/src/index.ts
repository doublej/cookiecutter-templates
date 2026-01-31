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

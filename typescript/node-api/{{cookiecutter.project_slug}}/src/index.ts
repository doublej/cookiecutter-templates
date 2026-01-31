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

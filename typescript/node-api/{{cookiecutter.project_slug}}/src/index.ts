import { cors } from '@elysiajs/cors'
import { swagger } from '@elysiajs/swagger'
import { Elysia } from 'elysia'
import { env } from './env.js'
import { negotiate, t } from './i18n.js'
import { logger } from './logger.js'

const app = new Elysia()
  .use(cors())
  .use(swagger())
  .get('/health', () => ({ status: 'ok', timestamp: new Date().toISOString() }))
  .derive(({ headers, set }) => {
    const locale = negotiate(headers['accept-language'])
    set.headers['content-language'] = locale
    set.headers.vary = [set.headers.vary, 'Accept-Language'].filter(Boolean).join(', ')
    return { locale }
  })
  .get('/', ({ locale }) => ({
    message: t(locale, 'hello', { name: '{{ cookiecutter.project_name }}' }),
    uptime: t(locale, 'uptime', { count: Math.floor(process.uptime()) }),
  }))
  .listen({ port: env.PORT, hostname: env.HOST })

logger.info(`Server running at http://${env.HOST}:${env.PORT}`)

export { app }

import { createEnv } from '@t3-oss/env-core'
import { z } from 'zod'

export const env = createEnv({
  server: {
    NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
{% if cookiecutter.project_type == 'api' %}
    PORT: z.coerce.number().default(3000),
    HOST: z.string().default('0.0.0.0'),
{% endif %}
  },
  runtimeEnv: process.env,
  emptyStringAsUndefined: true,
})

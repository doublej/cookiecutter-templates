FROM oven/bun:1 AS base
WORKDIR /app

FROM base AS deps
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile

FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN bun run build

FROM base AS runtime
COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json ./

{% if cookiecutter.project_type == 'api' %}
ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000
CMD ["bun", "run", "start"]
{% elif cookiecutter.project_type == 'worker' %}
ENV NODE_ENV=production
CMD ["bun", "run", "start"]
{% else %}
CMD ["bun", "run", "start"]
{% endif %}

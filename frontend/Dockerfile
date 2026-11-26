FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

FROM deps AS dev
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM deps AS build
RUN npm run build

# Use Alpine's own signed stable repositories for the patched Nginx package.
FROM alpine:3.24 AS prod
RUN apk upgrade --no-cache \
    && apk add --no-cache 'nginx>=1.30.7-r0' gettext-envsubst \
    && apk info -v nginx
ENV API_UPSTREAM=api:8000
COPY nginx.conf.template /etc/nginx/cdc-server.conf.template
COPY nginx-runtime.conf /etc/nginx/cdc.conf
COPY --from=build /app/dist /usr/share/nginx/html
USER nginx
EXPOSE 3000
HEALTHCHECK --interval=20s --timeout=5s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:3000/healthz || exit 1
CMD ["sh", "-c", "envsubst '${API_UPSTREAM}' < /etc/nginx/cdc-server.conf.template > /tmp/cdc-server.conf && exec nginx -c /etc/nginx/cdc.conf -g 'daemon off;'"]

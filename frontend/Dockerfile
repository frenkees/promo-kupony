# Stage 1: build Vue app
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Build-time env: prefix QR kódů, předáno z docker-compose build args
ARG QR_PREFIX=PROMO
ENV VITE_QR_PREFIX=$QR_PREFIX
RUN npm run build

# Stage 2: serve with Caddy
FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile

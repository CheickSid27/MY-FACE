FROM node:20-alpine AS builder
WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

# Les variables NEXT_PUBLIC_* sont figees dans le bundle JS a la compilation
# (pas au demarrage du process) : il faut donc les passer en build args, pas
# seulement en env_file docker-compose, sinon le build embarque les valeurs
# par defaut au lieu de celles de .env. Voir docs/DEPLOYMENT.md : tout
# changement de NEXT_PUBLIC_API_URL (ex: rotation d'URL de tunnel) demande
# maintenant un rebuild (`docker compose build frontend`), pas juste un
# restart, contrairement au mode dev precedent.
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_PAYMENT_PROVIDER
ARG NEXT_PUBLIC_VAPID_PUBLIC_KEY
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_PAYMENT_PROVIDER=$NEXT_PUBLIC_PAYMENT_PROVIDER
ENV NEXT_PUBLIC_VAPID_PUBLIC_KEY=$NEXT_PUBLIC_VAPID_PUBLIC_KEY

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]

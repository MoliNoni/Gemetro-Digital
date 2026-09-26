# Gemetro Digital frontend — static Vite build served by nginx (local docker-compose).
# In production the frontend is deployed to Vercel instead (frontend/vercel.json).
FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# The API base URL is baked into the bundle at build time (import.meta.env.VITE_API_URL).
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

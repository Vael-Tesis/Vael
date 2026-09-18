# syntax=docker/dockerfile:1
# Dev server de Vite para docker-compose local. El build de producción (npm run build)
# se despliega a S3+CloudFront vía CI/CD — no a través de esta imagen.

FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

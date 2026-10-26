# Imagen de desarrollo del frontend para docker-compose (DEC-008).
# En producción el build estático se publica en S3 detrás de CloudFront (DEC-018); esta imagen no se despliega.
FROM node:24-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM node:20-alpine

WORKDIR /app

COPY apps/assessment-engine/package.json ./
RUN npm install

COPY apps/assessment-engine/. .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]

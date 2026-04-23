FROM node:20-alpine

WORKDIR /app

COPY apps/candidate-portal/package.json ./
RUN npm install

COPY apps/candidate-portal/. .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]

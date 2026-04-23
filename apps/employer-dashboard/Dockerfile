FROM node:20-alpine

WORKDIR /app

COPY apps/employer-dashboard/package.json ./
RUN npm install

COPY apps/employer-dashboard/. .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]

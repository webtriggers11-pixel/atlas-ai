FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json .
RUN npm install

COPY . .

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM node:20-alpine

WORKDIR /app

COPY --from=build /app/package.json /app/package-lock.json .
RUN npm install --omit=dev

COPY --from=build /app/dist ./dist

EXPOSE 5173
CMD ["npm", "run", "start"]

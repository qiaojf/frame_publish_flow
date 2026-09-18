FROM node:22-alpine AS build
ARG VITE_DEFAULT_LOCALE=zh-CN
ARG VITE_DISPLAY_TIME_ZONE=Asia/Tokyo
ENV VITE_DEFAULT_LOCALE=$VITE_DEFAULT_LOCALE
ENV VITE_DISPLAY_TIME_ZONE=$VITE_DISPLAY_TIME_ZONE
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

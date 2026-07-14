# 前端：构建阶段 + Nginx 运行阶段
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json .
RUN npm install

COPY . .
# 注入后端地址（compose 中通过 args 传入）；缺省走同源 /api/v1
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# 运行阶段
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

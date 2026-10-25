# Baseline image build. The ordering below is intentionally naive: the whole app is copied
# before `npm ci`, so any source change invalidates the dependency layer. Layer-cache
# optimisation is introduced (and measured) in a later phase of the project.

FROM node:20 AS build
WORKDIR /app
COPY . .
RUN npm ci && npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# --- Stage 1: Development (The "Base" Image) ---
FROM node:22-alpine as development

WORKDIR /app

# Copy package.json to cache dependencies
COPY package*.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy the source code 
COPY . .

# Default command for dev 
CMD ["npm", "run", "dev"]

# --- Stage 2: Build (Compiles the App) ---
FROM development as build
RUN npm run build

# --- Stage 3: Production (Serve with Nginx) ---
FROM nginx:alpine as production

# Copy the build output from Stage 2 to Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Copy the custom Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
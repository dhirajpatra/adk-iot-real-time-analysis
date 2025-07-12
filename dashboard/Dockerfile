# dashboard/Dockerfile
FROM nginx:alpine
# Copy your static website files to Nginx's default public directory
COPY . /usr/share/nginx/html
EXPOSE 80
# Command to run Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
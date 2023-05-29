# Build Stage
FROM python:3.11-alpine as build

# Upgrade pip and install necessary utilities
RUN pip install --upgrade pip
RUN apk add --no-cache git

# Set working directory
WORKDIR /app

# Clone the latest release from the Git repository
RUN git clone https://github.com/klivolks/Flask-Gateway.git /app

# Rename .env-example to .env and write a secret key
RUN mv /app/.env-example /app/.env

# Generate a unique secret key and append it to .env file
RUN echo "SECRET_KEY=`python -c 'import secrets; print(secrets.token_urlsafe(16))'`" >> /app/.env

# Install the Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Production Stage
FROM python:3.11-alpine

# Install nginx and supervisord
RUN apk add --no-cache nginx supervisor

# Copy the Python environment and application from the build stage
COPY --from=build /usr/local /usr/local
COPY --from=build /app /app

# Install utilities
RUN apk update && \
    apk add curl htop

# Nginx configuration
RUN printf "events { worker_connections 1024; }\nhttp {\n\tserver {\n\t\tlisten 80;\n\t\tlocation / {\n\t\t\tproxy_pass http://127.0.0.1:5001;\n\t\t\tproxy_set_header Host \$host;\n\t\t\tproxy_set_header X-Real-IP \$remote_addr;\n\t\t}\n\t}\n}" > /etc/nginx/nginx.conf

# Create supervisor configuration and write supervisord configuration
RUN mkdir -p /etc/supervisor/conf.d && \
    echo -e "\
[supervisord]\n\
nodaemon=true\n\
\n\
[program:flask]\n\
command=python /app/app.py\n\
directory=/app\n\
autostart=true\n\
autorestart=true\n\
redirect_stderr=true\n\
\n\
[program:nginx]\n\
command=nginx -g 'daemon off;'\n\
autostart=true\n\
autorestart=true\n\
redirect_stderr=true\n\
" > /etc/supervisor/conf.d/supervisord.conf

# Expose the necessary port
EXPOSE 80

# Set the CMD to supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

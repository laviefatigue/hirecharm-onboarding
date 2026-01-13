# HireCharm Onboarding Form
# Serves static form + FastAPI backend for submissions

FROM python:3.11-alpine

# Install nginx and build dependencies
RUN apk add --no-cache nginx postgresql-dev gcc musl-dev

# Create app directory
WORKDIR /app

# Copy and install Python dependencies
COPY api/requirements.txt /app/api/
RUN pip install --no-cache-dir -r /app/api/requirements.txt

# Copy application files
COPY api/ /app/api/
COPY index.html /usr/share/nginx/html/index.html
COPY nginx.conf /etc/nginx/http.d/default.conf
COPY start.sh /app/start.sh

# Make start script executable
RUN chmod +x /app/start.sh

# Expose port 80
EXPOSE 80

# Start both services
CMD ["/app/start.sh"]

# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create startup script
RUN echo '#!/bin/bash\n\
python manage.py migrate\n\
exec gunicorn clauseguard.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 30\n\
' > /start.sh && chmod +x /start.sh

CMD ["/start.sh"]
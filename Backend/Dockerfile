FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FLASK_ENV=production
WORKDIR /workspace/Backend
RUN useradd --create-home appuser
COPY Backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY Backend /workspace/Backend
COPY frontend /workspace/frontend
RUN mkdir -p /workspace/Backend/instance/sessions && chown -R appuser:appuser /workspace
USER appuser
EXPOSE 10000
CMD ["sh", "-c", "flask --app wsgi.py db upgrade && exec gunicorn --bind 0.0.0.0:${PORT:-10000} wsgi:app"]

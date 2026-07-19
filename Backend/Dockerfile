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
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["sh", "-c", "flask --app wsgi.py db upgrade && exec gunicorn -b 0.0.0.0:8000 wsgi:app"]

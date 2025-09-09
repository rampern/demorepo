FROM python:3.10-slim

WORKDIR /app

COPY ./backend /app

RUN pip install --no-cache-dir fastapi uvicorn httpx sqlalchemy psycopg2-binary bcrypt PyJWT python-multipart

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

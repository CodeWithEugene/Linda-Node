FROM node:20-alpine AS frontend-build
WORKDIR /workspace/client/frontend
COPY client/frontend/package.json client/frontend/package-lock.json ./
RUN npm ci
COPY client/frontend ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATABASE_URL=sqlite:///var/linda.db
RUN apt-get update && apt-get install -y --no-install-recommends libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev && rm -rf /var/lib/apt/lists/*
COPY server/backend /app
COPY --from=frontend-build /workspace/client/frontend/dist /app/static
RUN pip install --no-cache-dir .
RUN mkdir -p /app/var
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

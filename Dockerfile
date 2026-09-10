FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-build /frontend/dist ./static

ENV DATABASE_PATH=/data/shopping.db
EXPOSE 5000

# --worker-class gthread + --threads: SSE (/api/events) holds a connection
# open indefinitely per client, which would permanently tie up a sync
# worker per connected client. Threads release the GIL while blocked on
# queue.get() (see backend/events.py), so this lets one worker serve many
# open SSE connections plus normal requests concurrently.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--worker-class", "gthread", "--threads", "8", "app:app"]

# Stage 1: Build the Vite frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/UI/web
COPY UI/web/package*.json ./
RUN npm install
COPY UI/web ./
RUN npm run build

# Stage 2: Backend + Java Environment
FROM python:3.10-slim
# Install Java (needed for JPype and RefactoringMiner) and git
RUN apt-get update && \
    apt-get install -y default-jre git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and service code
COPY . .

# Copy built frontend into the backend directory
COPY --from=frontend-builder /app/UI/web/dist /app/UI/web/dist

# Expose the API and UI port
EXPOSE 5172

# Start the FastAPI server
CMD ["python", "UI/backend/server.py"]

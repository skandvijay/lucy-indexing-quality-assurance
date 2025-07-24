# 🐳 IndexingQA Docker Setup Guide

## 🚀 One-Command Deployment

The easiest way to run the complete IndexingQA Pipeline with all features working perfectly.

### ✅ Prerequisites

- **Docker** (20.10+): [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose** (2.0+): Usually included with Docker Desktop

### 🏃‍♂️ Quick Start

```bash
# 1. Clone the repository
git clone <your-repository-url>
cd indexing-qa-main

# 2. Start the application (builds automatically)
docker-compose up --build

# 3. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

**🎉 That's it! The complete system is running with:**
- ✅ All 225 existing records loaded
- ✅ All dynamic thresholds working
- ✅ Frontend and backend integrated
- ✅ Production-ready configuration

---

## 🔧 Detailed Setup Options

### Option 1: Docker Compose (Recommended)

```bash
# Development mode (with hot reload)
docker-compose up --build

# Production mode (detached, optimized)
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop the application
docker-compose down

# Full cleanup (removes volumes too)
docker-compose down -v
```

### Option 2: Docker Only

```bash
# Build the image
docker build -t indexing-qa .

# Run the container
docker run -d \
  --name indexing-qa-app \
  -p 3000:3000 \
  -p 8000:8000 \
  -v indexing_qa_data:/app/backend \
  indexing-qa

# View logs
docker logs -f indexing-qa-app

# Stop and remove
docker stop indexing-qa-app && docker rm indexing-qa-app
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory to customize settings:

```bash
# ===========================================
# AI/LLM Configuration (Optional)
# ===========================================
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# ===========================================  
# Quality Thresholds (Defaults - Change via UI)
# ===========================================
APPROVAL_QUALITY_SCORE_THRESHOLD=50.0
SEMANTIC_RELEVANCE_THRESHOLD=0.15
DOMAIN_RELEVANCE_THRESHOLD=0.1
CONTEXT_COHERENCE_THRESHOLD=0.1
TAG_SPECIFICITY_THRESHOLD=0.5

# ===========================================
# LLM Invocation Settings  
# ===========================================
LLM_INVOCATION_MODE=percentage
LLM_PERCENTAGE_THRESHOLD=85.0
LLM_WEIGHTED_THRESHOLD=0.8
LLM_RANGE_MIN_THRESHOLD=70.0
LLM_RANGE_MAX_THRESHOLD=80.0

# ===========================================
# Performance Settings
# ===========================================
FASTAPI_WORKERS=1
MAX_REQUESTS=1000
REQUEST_TIMEOUT=30

# ===========================================
# Database Configuration
# ===========================================
DB_PATH=/app/backend/indexing_qa.db
ENABLE_DB_BACKUP=true
BACKUP_INTERVAL_HOURS=24
```

### Volume Mapping

The Docker container uses persistent volumes:

```yaml
volumes:
  - indexing_qa_data:/app/backend      # Database and backend files
  - indexing_qa_logs:/app/logs         # Application logs
  - indexing_qa_uploads:/app/uploads   # File uploads
```

---

## 📊 Monitoring & Health Checks

### Built-in Health Checks

The container includes automatic health monitoring:

```bash
# Check overall container health
docker ps
# Look for "healthy" status

# Manual health checks
curl http://localhost:8000/health     # Backend API
curl http://localhost:3000           # Frontend
```

### Viewing Logs

```bash
# All logs
docker-compose logs -f

# Backend only
docker-compose logs -f indexing-qa | grep "backend"

# Frontend only  
docker-compose logs -f indexing-qa | grep "frontend"

# Error logs only
docker-compose logs -f indexing-qa | grep -i error
```

### Performance Monitoring

```bash
# Container resource usage
docker stats indexing-qa-pipeline

# Detailed container info
docker inspect indexing-qa-pipeline

# Disk usage
docker system df
```

---

## 🚀 Production Deployment

### Using Docker Compose (Recommended)

```bash
# Production deployment
docker-compose -f docker-compose.yml up -d

# Scale for high availability
docker-compose up --scale indexing-qa=3 -d

# Update deployment
git pull
docker-compose build --no-cache
docker-compose up -d
```

### Using Docker Swarm

```bash
# Initialize swarm (if not already done)
docker swarm init

# Deploy as a stack
docker stack deploy -c docker-compose.yml indexing-qa-stack

# Scale the service
docker service scale indexing-qa-stack_indexing-qa=3

# Update the service
docker service update indexing-qa-stack_indexing-qa
```

### Using Kubernetes

```bash
# Generate Kubernetes manifests (using kompose)
kompose convert

# Apply to cluster
kubectl apply -f .

# Check deployment
kubectl get pods
kubectl get services
```

---

## 🛠️ Development & Debugging

### Development Mode

```bash
# Run with development overrides
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Shell into running container
docker exec -it indexing-qa-pipeline bash

# Run specific commands
docker exec indexing-qa-pipeline python backend/create_table.py
```

### Debugging Issues

```bash
# Check container startup
docker-compose logs indexing-qa

# Inspect container filesystem
docker exec -it indexing-qa-pipeline ls -la /app

# Check running processes
docker exec indexing-qa-pipeline ps aux

# Check network connectivity
docker exec indexing-qa-pipeline curl localhost:8000/health
```

### Database Access

```bash
# Access SQLite database
docker exec -it indexing-qa-pipeline sqlite3 /app/backend/indexing_qa.db

# Create database backup
docker exec indexing-qa-pipeline sqlite3 /app/backend/indexing_qa.db ".backup /app/backend/backup.db"

# Copy database out of container
docker cp indexing-qa-pipeline:/app/backend/indexing_qa.db ./backup_db.db
```

---

## 🔄 Updates & Maintenance

### Updating the Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verify update
curl http://localhost:8000/health
```

### Backup Strategy

```bash
# Create backup of volumes
docker run --rm -v indexing_qa_data:/data -v $(pwd):/backup alpine tar czf /backup/indexing_qa_backup.tar.gz /data

# Restore from backup
docker run --rm -v indexing_qa_data:/data -v $(pwd):/backup alpine tar xzf /backup/indexing_qa_backup.tar.gz -C /
```

### Cleanup

```bash
# Remove unused containers and images
docker system prune -a

# Remove specific volumes (⚠️ This deletes data!)
docker volume rm indexing_qa_data indexing_qa_logs indexing_qa_uploads

# Complete reset
docker-compose down -v
docker system prune -a --volumes
```

---

## 🆘 Troubleshooting

### Common Issues

**Problem**: Container fails to start
```bash
# Check logs for errors
docker-compose logs indexing-qa

# Verify ports aren't in use
lsof -i :3000
lsof -i :8000

# Try rebuilding
docker-compose build --no-cache
```

**Problem**: Cannot access frontend/backend
```bash
# Check container is running
docker ps

# Verify health
curl http://localhost:8000/health

# Check port mapping
docker port indexing-qa-pipeline
```

**Problem**: Database issues
```bash
# Check database file exists
docker exec indexing-qa-pipeline ls -la /app/backend/indexing_qa.db

# Verify database integrity
docker exec indexing-qa-pipeline sqlite3 /app/backend/indexing_qa.db "PRAGMA integrity_check;"
```

### Getting Help

1. **Check logs**: `docker-compose logs -f`
2. **Verify health**: `curl http://localhost:8000/health`
3. **Container inspection**: `docker inspect indexing-qa-pipeline`
4. **Resource usage**: `docker stats`
5. **Port conflicts**: `lsof -i :3000` and `lsof -i :8000`

---

## ✅ Success Verification

After deployment, verify everything is working:

```bash
# 1. Check containers are running
docker ps

# 2. Test backend health
curl http://localhost:8000/health

# 3. Test frontend access
curl -I http://localhost:3000

# 4. Test API endpoints
curl http://localhost:8000/stats

# 5. Test dynamic thresholds
curl http://localhost:8000/thresholds

# 6. Check record count
curl "http://localhost:8000/records?page=1&pageSize=1" | jq '.pagination.total'
```

**Expected Results:**
- ✅ All containers show "healthy" status
- ✅ Backend returns `{"status": "healthy"}`
- ✅ Frontend returns HTTP 200
- ✅ API returns valid JSON
- ✅ Thresholds show 23 configurable values
- ✅ Records show 225 total records

🎉 **Congratulations! Your IndexingQA Pipeline is fully operational!** 
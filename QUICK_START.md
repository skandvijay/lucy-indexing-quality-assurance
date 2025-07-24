# 🚀 Quick Start Guide

Get the Indexing QA Observability Tool running in under 5 minutes!

## ⚡ Automated Setup (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd indexing-qa-main

# Run automated setup
./setup.sh

# Start both servers
./start_all.sh
```

**🎯 That's it!** Visit http://localhost:3000 to use the application.

---

## 🔧 Manual Setup

### Prerequisites
- Python 3.8+ (`python3 --version`)
- Node.js 18+ (`node --version`)
- Git (`git --version`)

### Backend Setup (Terminal 1)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements/requirements.txt
python3 create_table.py
python3 run_local.py
```

### Frontend Setup (Terminal 2)
```bash
cd frontend
npm install
npm run dev
```

---

## 🌐 Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **Dashboard** | http://localhost:3000 | Main application interface |
| **API** | http://localhost:8000 | Backend API endpoints |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |

---

## 🧪 Quick Test

1. **Open Dashboard**: http://localhost:3000
2. **Test API**: http://localhost:8000/health
3. **Try Content Analysis**:
   ```bash
   curl -X POST http://localhost:8000/ingest \
     -H "Content-Type: application/json" \
     -d '{
       "document_text": "This is a comprehensive guide about machine learning deployment strategies.",
       "tags": ["machine-learning", "deployment", "guide"],
       "source_connector": "test"
     }'
   ```

---

## 📝 Key Features to Try

- **📊 Dashboard**: View processed records and quality metrics
- **🔍 Records**: Browse and filter content quality records
- **📈 Analytics**: Monitor system performance and trends
- **⚠️ Issues**: Review flagged content and quality issues
- **⚙️ Settings**: Configure thresholds and alert preferences

---

## 🚨 Common Issues & Quick Fixes

### Backend Won't Start
```bash
cd backend
source venv/bin/activate
python3 create_table.py  # Reinitialize database
python3 run_local.py
```

### Frontend Won't Start
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Port Already in Use
```bash
# Check what's using the port
lsof -i :8000  # Backend
lsof -i :3000  # Frontend

# Or use different ports
uvicorn run_local:app --port 8001  # Backend
npm run dev -- --port 3001         # Frontend
```

---

## 🎯 Development Workflow

```bash
# Daily startup
./start_all.sh

# Or manually:
# Terminal 1: cd backend && source venv/bin/activate && python3 run_local.py
# Terminal 2: cd frontend && npm run dev

# Access at http://localhost:3000
```

---

## 📚 Next Steps

1. **Read Full Documentation**: [README.md](README.md)
2. **Configure API Keys**: Update `backend/.env` for LLM features
3. **Explore API**: Visit http://localhost:8000/docs
4. **Test Quality Checks**: Use the dashboard to analyze content

---

## 🔧 Project Structure (Quick Reference)

```
indexing-qa-main/
├── backend/
│   ├── run_local.py         # Main server
│   ├── create_table.py      # Database setup
│   ├── app/                 # Application code
│   └── requirements/        # Dependencies
├── frontend/
│   ├── package.json         # Node.js config
│   └── src/                 # React components
├── setup.sh                 # Automated setup
├── start_all.sh            # Start both servers
└── README.md               # Full documentation
```

---

## 💡 Pro Tips

- **Use the automated setup**: `./setup.sh` handles everything
- **Start both servers**: `./start_all.sh` runs everything
- **Check logs**: Monitor terminal output for errors
- **Test incrementally**: Start with health checks, then try features
- **Update API keys**: Add real LLM keys to `backend/.env` for full functionality

---

**Need more details?** See the comprehensive [README.md](README.md) for complete documentation.

**Happy coding! 🚀** 
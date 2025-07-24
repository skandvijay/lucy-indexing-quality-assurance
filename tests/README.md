# 🧪 Tests Directory

This directory contains all test files, debug utilities, and test data for the Indexing QA Observability Tool.

## 📁 Directory Structure

```
tests/
├── backend/           # Backend-related tests
│   ├── unit/         # Unit tests for individual functions/classes
│   ├── integration/  # Integration tests for component interactions
│   └── api/          # API endpoint tests
├── frontend/         # Frontend-related tests
│   ├── pages/        # Test pages and components
│   └── components/   # Individual component tests
├── debug/            # Debug utilities and scripts
└── data/             # Test data files and fixtures
```

## 🗂️ File Descriptions

### Backend Tests (`/backend/`)

- **`unit/test_llm_invocation_modes.py`** - Unit tests for LLM invocation logic
- **`api/test_tags_endpoint.py`** - API endpoint testing for tags functionality

### Frontend Tests (`/frontend/`)

- **`pages/backend-test/`** - Backend connectivity testing page
- **`pages/api-test/`** - API testing interface

### Debug Utilities (`/debug/`)

- **`debug_llm_invocation.py`** - Debug script for LLM invocation issues

### Test Data (`/data/`)

- **`test-upload.json`** - Sample test data for upload functionality

## 🚀 Running Tests

### Backend Tests
```bash
# Run all backend tests
cd backend && python -m pytest ../tests/backend/

# Run specific test files
python -m pytest tests/backend/unit/test_llm_invocation_modes.py
python -m pytest tests/backend/api/test_tags_endpoint.py
```

### Frontend Tests
```bash
# Navigate to frontend directory
cd frontend

# Run development server for test pages
npm run dev

# Access test pages:
# - http://localhost:3001/backend-test
# - http://localhost:3001/api-test
```

### Debug Scripts
```bash
# Run debug utilities
cd backend && python ../tests/debug/debug_llm_invocation.py
```

## 📋 Test Categories

### 🔧 Unit Tests
- Individual function testing
- Isolated component testing
- Mock data testing

### 🔗 Integration Tests
- Component interaction testing
- Database integration testing
- API integration testing

### 🌐 API Tests
- Endpoint functionality testing
- Request/response validation
- Error handling testing

### 🖥️ Frontend Tests
- UI component testing
- User interaction testing
- API communication testing

## 📝 Adding New Tests

### For Backend:
1. **Unit tests** → `tests/backend/unit/`
2. **API tests** → `tests/backend/api/`
3. **Integration tests** → `tests/backend/integration/`

### For Frontend:
1. **Component tests** → `tests/frontend/components/`
2. **Page tests** → `tests/frontend/pages/`

### For Debug:
1. **Debug scripts** → `tests/debug/`

### For Test Data:
1. **Sample data** → `tests/data/`

## 🛠️ Test Environment

- **Backend**: Python with pytest
- **Frontend**: Next.js with built-in testing
- **Database**: SQLite for testing
- **API**: FastAPI test client

## 📊 Coverage

Aim for:
- **Unit tests**: 80%+ coverage
- **Integration tests**: Critical paths
- **API tests**: All endpoints
- **Frontend tests**: Core user flows

---

**Note**: This directory was organized from scattered test files to improve maintainability and test discoverability. 
#!/bin/bash

# =============================================================================
# INDEXING QA PIPELINE - SETUP SCRIPT
# =============================================================================
# Comprehensive setup script for development and production environments
# Version: 1.0.0

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="Indexing QA Pipeline"
REQUIRED_PYTHON_VERSION="3.11"
REQUIRED_NODE_VERSION="18"

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│                                                             │"
    echo "│          🧠 INDEXING QA PIPELINE SETUP                     │"
    echo "│                                                             │"
    echo "│    AI-Powered Quality Assurance for Knowledge Base         │"
    echo "│                                                             │"
    echo "└─────────────────────────────────────────────────────────────┘"
    echo -e "${NC}"
}

# Print section header
print_header() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Print success message
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Print warning message
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Print error message
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Print info message
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python() {
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [ "$(printf '%s\n' "$REQUIRED_PYTHON_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_PYTHON_VERSION" ]; then
            print_success "Python $PYTHON_VERSION found"
            return 0
        else
            print_error "Python $REQUIRED_PYTHON_VERSION+ required, found $PYTHON_VERSION"
            return 1
        fi
    else
        print_error "Python 3 not found"
        return 1
    fi
}

# Check Node.js version
check_node() {
    if command_exists node; then
        NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$NODE_VERSION" -ge "$REQUIRED_NODE_VERSION" ]; then
            print_success "Node.js v$NODE_VERSION found"
            return 0
        else
            print_error "Node.js $REQUIRED_NODE_VERSION+ required, found v$NODE_VERSION"
            return 1
        fi
    else
        print_error "Node.js not found"
        return 1
    fi
}

# Check Docker
check_docker() {
    if command_exists docker; then
        if docker info >/dev/null 2>&1; then
            print_success "Docker is running"
            return 0
        else
            print_warning "Docker is installed but not running"
            return 1
        fi
    else
        print_warning "Docker not found (optional for development)"
        return 1
    fi
}

# Setup Python environment
setup_python() {
    print_header "🐍 Setting up Python Environment"
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    print_info "Activating virtual environment..."
    source venv/bin/activate
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip setuptools wheel
    
    # Install dependencies
    print_info "Installing Python dependencies..."
    pip install -r requirements.txt
    print_success "Python dependencies installed"
}

# Setup Node.js environment
setup_node() {
    print_header "📦 Setting up Node.js Environment"
    
    cd frontend
    
    # Install dependencies
    print_info "Installing Node.js dependencies..."
    npm ci
    print_success "Node.js dependencies installed"
    
    cd ..
}

# Setup database
setup_database() {
    print_header "🗄️ Setting up Database"
    
    cd backend
    
    # Activate virtual environment
    source ../venv/bin/activate
    
    # Initialize database
    if [ ! -f "indexing_qa.db" ]; then
        print_info "Initializing database..."
        python create_table.py
        print_success "Database initialized"
    else
        print_info "Database already exists"
    fi
    
    cd ..
}

# Setup environment file
setup_env() {
    print_header "⚙️ Setting up Environment Configuration"
    
    if [ ! -f ".env" ]; then
        print_info "Creating .env file from template..."
        cp env.example .env
        print_success ".env file created"
        print_warning "Please edit .env file to add your API keys and configuration"
    else
        print_info ".env file already exists"
    fi
}

# Create necessary directories
create_directories() {
    print_header "📁 Creating Project Directories"
    
    directories=("logs" "data" "uploads" "backups")
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "Created directory: $dir"
        else
            print_info "Directory already exists: $dir"
        fi
    done
}

# Setup Docker environment
setup_docker() {
    print_header "🐳 Setting up Docker Environment"
    
    if check_docker; then
        print_info "Building Docker images..."
        docker-compose build
        print_success "Docker images built successfully"
        
        print_info "Starting services..."
        docker-compose up -d
        print_success "Docker services started"
        
        # Wait for services to be ready
        print_info "Waiting for services to be ready..."
        sleep 10
        
        # Check health
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            print_success "Backend is healthy"
        else
            print_warning "Backend health check failed"
        fi
        
        if curl -f http://localhost:3000 >/dev/null 2>&1; then
            print_warning "Frontend is starting (may take a moment)"
        fi
    else
        print_warning "Skipping Docker setup (Docker not available)"
    fi
}

# Start development servers
start_dev_servers() {
    print_header "🚀 Starting Development Servers"
    
    # Check if Docker is running the services
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        print_info "Services are already running via Docker"
        return 0
    fi
    
    print_info "Starting backend server..."
    cd backend
    source ../venv/bin/activate
    python start_api.py &
    BACKEND_PID=$!
    cd ..
    
    print_info "Starting frontend server..."
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    
    # Wait for servers to start
    print_info "Waiting for servers to start..."
    sleep 5
    
    # Check if servers are running
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        print_success "Backend server is running"
    else
        print_warning "Backend server may still be starting"
    fi
    
    print_info "Development servers started"
    print_info "Use Ctrl+C to stop servers"
    
    # Keep script running
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
    wait
}

# Print final instructions
print_final_instructions() {
    print_header "🎉 Setup Complete!"
    
    echo -e "${GREEN}"
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│                                                             │"
    echo "│               🎊 SETUP SUCCESSFUL! 🎊                     │"
    echo "│                                                             │"
    echo "│  Your Indexing QA Pipeline is ready to use!                │"
    echo "│                                                             │"
    echo "└─────────────────────────────────────────────────────────────┘"
    echo -e "${NC}"
    
    echo -e "\n${CYAN}📍 Access Points:${NC}"
    echo -e "   🖥️  Frontend:          ${BLUE}http://localhost:3000${NC}"
    echo -e "   🔧 Backend API:       ${BLUE}http://localhost:8000${NC}"
    echo -e "   📚 API Documentation: ${BLUE}http://localhost:8000/docs${NC}"
    echo -e "   ❤️  Health Check:      ${BLUE}http://localhost:8000/health${NC}"
    echo -e "   📊 Analytics:         ${BLUE}http://localhost:3000/analytics${NC}"
    echo -e "   ⚙️  Settings:          ${BLUE}http://localhost:3000/settings${NC}"
    
    echo -e "\n${CYAN}🚀 Quick Commands:${NC}"
    echo -e "   Start with Docker:     ${YELLOW}docker-compose up${NC}"
    echo -e "   Stop Docker:           ${YELLOW}docker-compose down${NC}"
    echo -e "   View logs:             ${YELLOW}docker-compose logs -f${NC}"
    echo -e "   Development mode:      ${YELLOW}./setup.sh --dev${NC}"
    
    echo -e "\n${CYAN}📖 Next Steps:${NC}"
    echo -e "   1. Edit ${YELLOW}.env${NC} file to add your API keys"
    echo -e "   2. Visit the frontend to start using the application"
    echo -e "   3. Check the API documentation for integration details"
    echo -e "   4. Configure quality thresholds in the settings"
    
    if [ ! -s ".env" ] || grep -q "your_.*_key_here" ".env" 2>/dev/null; then
        echo -e "\n${YELLOW}⚠️  Remember to configure your API keys in the .env file for full functionality${NC}"
    fi
}

# Main setup function
main() {
    print_banner
    
    # Parse command line arguments
    DOCKER_ONLY=false
    DEV_ONLY=false
    SKIP_DOCKER=false
    
    for arg in "$@"; do
        case $arg in
            --docker-only)
                DOCKER_ONLY=true
                shift
                ;;
            --dev|--development)
                DEV_ONLY=true
                SKIP_DOCKER=true
                shift
                ;;
            --skip-docker)
                SKIP_DOCKER=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --docker-only    Setup using Docker only"
                echo "  --dev            Setup for development (skip Docker)"
                echo "  --skip-docker    Skip Docker setup"
                echo "  --help, -h       Show this help message"
                echo ""
                exit 0
                ;;
        esac
    done
    
    # Prerequisites check
    print_header "🔍 Checking Prerequisites"
    
    PYTHON_OK=false
    NODE_OK=false
    DOCKER_OK=false
    
    if check_python; then PYTHON_OK=true; fi
    if check_node; then NODE_OK=true; fi
    if check_docker; then DOCKER_OK=true; fi
    
    # Determine setup mode
    if [ "$DOCKER_ONLY" = true ]; then
        if [ "$DOCKER_OK" = false ]; then
            print_error "Docker is required for --docker-only mode"
            exit 1
        fi
        print_info "Running Docker-only setup"
        create_directories
        setup_env
        setup_docker
    elif [ "$DEV_ONLY" = true ]; then
        if [ "$PYTHON_OK" = false ] || [ "$NODE_OK" = false ]; then
            print_error "Python 3.11+ and Node.js 18+ are required for development mode"
            exit 1
        fi
        print_info "Running development-only setup"
        create_directories
        setup_env
        setup_python
        setup_node
        setup_database
        start_dev_servers
    else
        # Full setup
        if [ "$PYTHON_OK" = true ] && [ "$NODE_OK" = true ]; then
            create_directories
            setup_env
            setup_python
            setup_node
            setup_database
            
            if [ "$SKIP_DOCKER" = false ] && [ "$DOCKER_OK" = true ]; then
                setup_docker
            else
                start_dev_servers
            fi
        elif [ "$DOCKER_OK" = true ]; then
            print_warning "Python/Node.js not available, using Docker-only setup"
            create_directories
            setup_env
            setup_docker
        else
            print_error "Neither development tools nor Docker are available"
            print_info "Please install Python 3.11+, Node.js 18+, or Docker"
            exit 1
        fi
    fi
    
    print_final_instructions
}

# Run main function
main "$@" 
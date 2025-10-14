#!/bin/bash

# Gmail Chat Application Setup and Start Script
# This script sets up the environment and starts both the API and Streamlit UI

set -e  # Exit on any error

echo "🚀 Starting Gmail Chat Application Setup..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
check_python() {
    print_status "Checking Python installation..."
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        print_success "Python3 found: $(python3 --version)"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        print_success "Python found: $(python --version)"
    else
        print_error "Python is not installed. Please install Python 3.8+ first."
        exit 1
    fi
}

# Check if uv is installed
check_uv() {
    print_status "Checking uv installation..."
    if command -v uv &> /dev/null; then
        print_success "uv found: $(uv --version)"
    else
        print_error "uv is not installed. Please install uv first."
        print_error "You can install it with: pip install uv"
        exit 1
    fi
}

# uv will automatically manage the virtual environment

# Install dependencies
install_dependencies() {
    print_status "Installing dependencies using uv..."
    
    # Install main requirements using uv pip install
    if [ -f "requirements.txt" ]; then
        print_status "Installing main requirements..."
        uv pip install -r requirements.txt
    fi
    
    # Install agent_builder_client requirements using uv pip install
    if [ -f "agent_builder_client/requirements.txt" ]; then
        print_status "Installing agent_builder_client requirements..."
        uv pip install -r agent_builder_client/requirements.txt
    fi
    
    print_success "All dependencies installed using uv"
}

# Check if required files exist
check_files() {
    print_status "Checking required files..."
    
    local missing_files=()
    
    if [ ! -f "agent_builder_client/api.py" ]; then
        missing_files+=("agent_builder_client/api.py")
    fi
    
    if [ ! -f "streamlit_chat_ui.py" ]; then
        missing_files+=("streamlit_chat_ui.py")
    fi
    
    if [ ! -f "agent_builder_client/config.py" ]; then
        missing_files+=("agent_builder_client/config.py")
    fi
    
    if [ ${#missing_files[@]} -ne 0 ]; then
        print_error "Missing required files:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        exit 1
    fi
    
    print_success "All required files found"
}

# Check if credentials.json exists
check_credentials() {
    print_status "Checking Google OAuth2 credentials..."
    if [ ! -f "credentials.json" ]; then
        print_warning "credentials.json not found"
        print_warning "Please download your Google OAuth2 credentials and save as 'credentials.json'"
        print_warning "You can continue without it, but Gmail fetching will not work"
    else
        print_success "Google OAuth2 credentials found"
    fi
}

# Check if multilingual-e5-large model exists
check_model() {
    print_status "Checking embedding model..."
    if [ ! -d "multilingual-e5-large" ]; then
        print_warning "multilingual-e5-large model directory not found"
        print_warning "Please download the model first:"
        print_warning "git clone https://huggingface.co/intfloat/multilingual-e5-large"
        print_warning "You can continue without it, but the API may not work properly"
    else
        print_success "Embedding model found"
    fi
}

# Start API service
start_api() {
    print_status "Starting FastAPI service..."
    
    # Change to agent_builder_client directory
    cd agent_builder_client
    
    # Start API in background using uv run
    uv run api.py &
    API_PID=$!
    
    # Go back to root directory
    cd ..
    
    print_success "FastAPI service started (PID: $API_PID)"
    
    # Wait a bit for the API to start
    sleep 3
    
    # Check if API is running
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        print_success "API service is healthy and running on http://localhost:8080"
    else
        print_warning "API service may not be ready yet. Please check manually."
    fi
}

# Start Streamlit UI
start_streamlit() {
    print_status "Starting Streamlit UI..."
    
    # Start Streamlit in background using uv run
    uv run streamlit run streamlit_chat_ui.py --server.headless true &
    STREAMLIT_PID=$!
    
    print_success "Streamlit UI started (PID: $STREAMLIT_PID)"
    print_success "Streamlit UI is running (default port)"
}

# Main execution
main() {
    echo "=========================================="
    echo "📧 Gmail Chat Application Setup & Start"
    echo "=========================================="
    
    # Pre-flight checks
    check_python
    check_uv
    check_files
    
    # Setup environment
    install_dependencies
    
    # Additional checks
    check_credentials
    check_model
    
    echo ""
    echo "=========================================="
    echo "🚀 Starting Services..."
    echo "=========================================="
    
    # Start services
    start_api
    start_streamlit
    
    echo ""
    echo "=========================================="
    echo "✅ Setup Complete!"
    echo "=========================================="
    echo ""
    echo "🌐 Services are now running:"
    echo "   📡 FastAPI: http://localhost:8080"
    echo "   🖥️  Streamlit UI: http://localhost:8501 (default port)"
    echo ""
    echo "📋 API Endpoints:"
    echo "   - Health Check: http://localhost:8080/health"
    echo "   - API Docs: http://localhost:8080/docs"
    echo "   - Create DB: http://localhost:8080/create_db"
    echo "   - Query: http://localhost:8080/query_group"
    echo ""
    echo "🛑 To stop services, press Ctrl+C or run:"
    echo "   kill $API_PID $STREAMLIT_PID"
    echo ""
    echo "📖 For more information, check the README.md file"
    echo ""
    
    # Keep the script running
    print_status "Services are running. Press Ctrl+C to stop all services..."
    
    # Function to cleanup on exit
    cleanup() {
        echo ""
        print_status "Stopping services..."
        kill $API_PID $STREAMLIT_PID 2>/dev/null || true
        print_success "All services stopped"
        exit 0
    }
    
    # Set trap to cleanup on script exit
    trap cleanup SIGINT SIGTERM
    
    # Wait for user to stop
    wait
}

# Run main function
main "$@"

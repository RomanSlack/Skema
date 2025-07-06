#!/bin/bash

# Skema Development Startup Script
# This script sets up and starts the development environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[SKEMA]${NC} $1"
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

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for service to be ready
wait_for_service() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=0

    print_status "Waiting for $service to be ready..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s "$url" >/dev/null 2>&1; then
            print_success "$service is ready!"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    print_error "$service failed to start within expected time"
    return 1
}

# Main script
main() {
    print_status "Starting Skema Development Environment"
    echo

    # Check prerequisites
    print_status "Checking prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi

    print_success "Prerequisites check passed"
    echo

    # Check for .env file
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from .env.example..."
        cp .env.example .env
        print_warning "Please review and update the .env file with your settings."
        echo
    fi

    # Build and start services
    print_status "Building and starting services..."
    docker-compose down --remove-orphans 2>/dev/null || true
    docker-compose build
    docker-compose up -d

    echo
    print_status "Services started. Waiting for them to be ready..."

    # Wait for services to be ready
    wait_for_service "Database" "http://localhost:8080" || true  # Adminer for DB check
    wait_for_service "Backend API" "http://localhost:8000/health"
    wait_for_service "Frontend" "http://localhost:3000"

    echo
    print_success "Skema development environment is ready!"
    echo
    
    # Print access information
    echo "🌐 Access your application:"
    echo "   Frontend:  http://localhost:3000"
    echo "   Backend API: http://localhost:8000"
    echo "   API Docs:  http://localhost:8000/docs"
    echo "   Database Admin: http://localhost:8080 (adminer)"
    echo
    
    echo "📊 Default credentials:"
    echo "   Demo User: demo@skema.app / demo123"
    echo "   Database: skema_user / skema_password"
    echo
    
    echo "🔧 Useful commands:"
    echo "   View logs: docker-compose logs -f [service_name]"
    echo "   Stop: docker-compose down"
    echo "   Restart: docker-compose restart [service_name]"
    echo "   Shell access: docker-compose exec [service_name] /bin/bash"
    echo
    
    echo "📚 Next steps:"
    echo "   1. Open http://localhost:3000 in your browser"
    echo "   2. Login with demo@skema.app / demo123"
    echo "   3. Explore the Kanban boards, calendar, and journal features"
    echo "   4. Try the AI command bar with Cmd+K (Mac) or Ctrl+K (Windows/Linux)"
    echo
    
    # Offer to show logs
    read -p "Would you like to view the application logs? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Showing application logs (Ctrl+C to exit)..."
        docker-compose logs -f
    fi
}

# Handle script interruption
trap 'print_warning "Script interrupted"; exit 1' INT

# Run main function
main "$@"
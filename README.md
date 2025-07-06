# Skema - Production-Ready Productivity Suite

A comprehensive productivity application that unifies Kanban boards, calendar management, journal entries, and AI-powered command functionality into a single, elegant platform.

## 🚀 Features

### Core Functionality
- **📋 Kanban Boards**: Drag-and-drop task management with customizable columns
- **📅 Calendar**: Full-featured calendar with event management and recurring events
- **📝 Journal**: Rich text journal entries with mood tracking and search
- **🤖 AI Command Bar**: Natural language command processing with voice input support

### Technical Highlights
- **⚡ Real-time Collaboration**: WebSocket-powered live updates
- **🎨 Modern UI**: Responsive design with dark/light themes and custom color palettes
- **🔒 Enterprise Security**: JWT authentication, rate limiting, and audit logging
- **📊 Performance**: Optimized database queries with <200ms response times
- **♿ Accessibility**: WCAG 2.1 AA compliant with keyboard navigation
- **🌐 Production Ready**: Docker containerization with monitoring and backups

## 🏗️ Architecture

### Tech Stack
- **Frontend**: Next.js 15.2.0 + React 19 + TypeScript + Tailwind CSS
- **Backend**: FastAPI + SQLModel + PostgreSQL + Redis
- **Database**: PostgreSQL 15 with JSONB for flexible data storage
- **Deployment**: Docker Compose with Nginx reverse proxy
- **State Management**: Zustand + React Query for optimal caching
- **Real-time**: WebSocket connections for live collaboration

### Project Structure
```
Skema/
├── Frontend/           # Next.js application
├── Backend/            # FastAPI application
├── docker/             # Docker configurations
├── scripts/            # Utility scripts
├── docs/               # Documentation and ADRs
├── database/           # Database schema and migrations
└── deployment/         # Production deployment configs
```

## 🚦 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git
- (Optional) Node.js 18+ and Python 3.11+ for local development

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Skema
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the development environment**
   ```bash
   ./scripts/start.sh
   # or use Make
   make start
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Database Admin: http://localhost:8080

### Default Credentials
- **Demo User**: `demo@skema.app` / `demo123`
- **Database**: `skema_user` / `skema_password`

## 📖 Usage

### Getting Started
1. Open http://localhost:3000 in your browser
2. Login with the demo credentials or register a new account
3. Explore the different modules:
   - **Dashboard**: Overview of your productivity metrics
   - **Boards**: Create and manage Kanban boards
   - **Calendar**: Schedule and track events
   - **Journal**: Write and organize journal entries
   - **Settings**: Customize your experience

### AI Command Bar
- Press `Cmd+K` (Mac) or `Ctrl+K` (Windows/Linux) to open
- Type natural language commands like:
  - "Create a new board called Project Alpha"
  - "Schedule a meeting tomorrow at 2 PM"
  - "Add a journal entry about today"

### Key Features

#### Kanban Boards
- Create unlimited boards with custom columns
- Drag and drop cards between columns
- Add tags, due dates, and descriptions
- Real-time collaboration with team members

#### Calendar Management
- Multiple view modes (month/week/day)
- Recurring event support
- Reminder notifications
- Event categorization and color coding

#### Journal Entries
- Rich text editing with markdown support
- Mood tracking and analytics
- Tag-based organization
- Full-text search across all entries

## 🛠️ Development

### Available Commands

Using Make (recommended):
```bash
make start          # Start development environment
make stop           # Stop all services
make logs           # View application logs
make test           # Run all tests
make lint           # Run code linting
make backup         # Create database backup
make clean          # Clean up Docker resources
```

Using Docker Compose directly:
```bash
docker-compose up -d        # Start services
docker-compose down         # Stop services
docker-compose logs -f      # View logs
docker-compose restart     # Restart services
```

### Development Workflow

1. **Backend Development**
   ```bash
   cd Backend
   # Activate virtual environment
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or venv\Scripts\activate  # Windows
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run development server
   uvicorn app.main:app --reload
   ```

2. **Frontend Development**
   ```bash
   cd Frontend
   # Install dependencies
   npm install
   
   # Run development server
   npm run dev
   ```

3. **Database Migrations**
   ```bash
   # Create new migration
   make shell-backend
   alembic revision --autogenerate -m "Description"
   
   # Apply migrations
   alembic upgrade head
   ```

### Testing

```bash
# Run all tests
make test

# Run specific test suites
make test-backend    # Backend unit/integration tests
make test-frontend   # Frontend component tests
make test-e2e        # End-to-end tests
```

### Code Quality

```bash
# Run linters
make lint

# Format code
make format

# Type checking
make typecheck

# Security scan
make security-scan
```

## 🚀 Deployment

### Production Deployment

1. **Prepare environment**
   ```bash
   cp .env.example .env.production
   # Configure production values
   ```

2. **Deploy with Docker Compose**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Set up SSL certificates**
   ```bash
   # For development/testing
   make ssl-cert
   
   # For production, use Let's Encrypt or your certificate provider
   ```

### Environment Variables

Key environment variables to configure:

```bash
# Security
SECRET_KEY=your-super-secret-key
CORS_ORIGINS=https://yourdomain.com

# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# AI Integration
OPENAI_API_KEY=your-openai-key

# Frontend
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com
```

See `.env.example` for complete configuration options.

### Monitoring and Maintenance

```bash
# Health checks
make health

# Create backups
make backup

# View service status
make status

# Monitor logs
make logs
```

## 📚 API Documentation

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Token refresh
- `GET /api/auth/me` - Current user info

### Boards & Cards
- `GET /api/boards` - List boards
- `POST /api/boards` - Create board
- `GET /api/boards/{id}/cards` - List cards
- `PUT /api/cards/{id}/move` - Move card

### Calendar
- `GET /api/calendar/events` - List events
- `POST /api/calendar/events` - Create event
- `PUT /api/calendar/events/{id}` - Update event

### Journal
- `GET /api/journal/entries` - List entries
- `POST /api/journal/entries` - Create entry
- `GET /api/journal/search` - Search entries

### AI Commands
- `POST /api/ai/command` - Execute AI command
- `GET /api/ai/history` - Command history

For complete API documentation, visit http://localhost:8000/docs

## 🔒 Security

### Security Features
- JWT-based authentication with refresh tokens
- Rate limiting and request throttling
- CORS configuration for cross-origin requests
- Input validation and sanitization
- SQL injection prevention
- XSS protection with Content Security Policy
- HTTPS enforcement in production
- Audit logging for all data modifications

### Security Best Practices
- Use strong, unique passwords
- Enable two-factor authentication (when available)
- Regularly update dependencies
- Monitor security logs
- Use HTTPS in production
- Implement proper backup strategies

## 🤝 Contributing

### Development Guidelines
1. Follow the existing code style and conventions
2. Write tests for new functionality
3. Update documentation for API changes
4. Use meaningful commit messages
5. Create feature branches for new development

### Code Style
- **Backend**: Follow PEP 8 with Black formatting
- **Frontend**: Use Prettier with ESLint rules
- **Commits**: Use conventional commit format

### Pull Request Process
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and documentation
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Next.js team for the excellent React framework
- FastAPI team for the modern Python web framework
- PostgreSQL team for the robust database system
- Tailwind CSS team for the utility-first CSS framework
- All open-source contributors who made this project possible

## 📞 Support

### Getting Help
- 📖 Check the documentation in the `docs/` directory
- 🐛 Report bugs via GitHub Issues
- 💬 Join our community discussions
- 📧 Contact support for enterprise inquiries

### Common Issues

**Services won't start?**
- Check if Docker is running
- Verify ports 3000, 8000, 5432 are available
- Review Docker logs: `make logs`

**Database connection errors?**
- Ensure PostgreSQL container is healthy
- Check database credentials in `.env`
- Try resetting the database: `make db-reset`

**Frontend build failures?**
- Clear node_modules: `make reset-frontend`
- Check for TypeScript errors: `make typecheck`
- Verify environment variables

---

**Built with ❤️ for productivity enthusiasts**

Start your productivity journey today: `make start`
# Skema API

Production-ready FastAPI backend for the Skema productivity application.

## Features

- **Authentication & Authorization**: JWT-based authentication with refresh tokens
- **Kanban Boards**: Create and manage boards with cards, drag-and-drop functionality
- **Calendar**: Schedule and manage events with reminders and recurrence
- **Journal**: Personal journaling with mood tracking and search
- **AI Command Bar**: AI-powered command interface for productivity
- **Real-time Updates**: WebSocket support for live collaboration
- **Security**: Rate limiting, CORS, security headers, input validation
- **Monitoring**: Comprehensive logging, error handling, and health checks
- **Production Ready**: Docker, database migrations, automated testing

## Tech Stack

- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL with SQLModel/SQLAlchemy
- **Authentication**: JWT with refresh tokens
- **Real-time**: WebSockets
- **Caching**: Redis
- **Migration**: Alembic
- **Testing**: Pytest
- **Containerization**: Docker & Docker Compose
- **Code Quality**: Black, isort, flake8, mypy

## Quick Start

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd skema/Backend
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Run database migrations**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

5. **Access the API**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

### Local Development (without Docker)

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL and Redis**
   ```bash
   # Start PostgreSQL (example with Homebrew on macOS)
   brew services start postgresql
   createdb skema
   
   # Start Redis
   brew services start redis
   ```

3. **Configure environment**
   ```bash
   export DATABASE_URL="postgresql+asyncpg://username:password@localhost:5432/skema"
   export REDIS_URL="redis://localhost:6379"
   export JWT_SECRET_KEY="your-super-secret-key"
   ```

4. **Run migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start the server**
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current user info

### Boards (Kanban)
- `GET /api/boards` - List user's boards
- `POST /api/boards` - Create new board
- `GET /api/boards/{id}` - Get board with cards
- `PUT /api/boards/{id}` - Update board
- `DELETE /api/boards/{id}` - Delete board

### Cards
- `GET /api/boards/{id}/cards` - Get board cards
- `POST /api/boards/{id}/cards` - Create new card
- `PUT /api/cards/{id}` - Update card
- `PUT /api/cards/{id}/move` - Move card
- `DELETE /api/cards/{id}` - Delete card

### Calendar
- `GET /api/calendar/events` - List calendar events
- `POST /api/calendar/events` - Create new event
- `GET /api/calendar/events/{id}` - Get specific event
- `PUT /api/calendar/events/{id}` - Update event
- `DELETE /api/calendar/events/{id}` - Delete event

### Journal
- `GET /api/journal/entries` - List journal entries
- `POST /api/journal/entries` - Create new entry
- `GET /api/journal/entries/{id}` - Get specific entry
- `PUT /api/journal/entries/{id}` - Update entry
- `DELETE /api/journal/entries/{id}` - Delete entry
- `GET /api/journal/stats` - Get journal statistics

### AI Commands
- `POST /api/ai/command` - Execute AI command
- `GET /api/ai/history` - Get command history
- `GET /api/ai/suggestions` - Get AI suggestions

### Health & Monitoring
- `GET /health` - Health check
- `GET /` - API information

## WebSocket

Connect to real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=your-jwt-token');

// Subscribe to board updates
ws.send(JSON.stringify({
  type: 'subscribe_board',
  board_id: 'board-uuid'
}));

// Listen for updates
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Update:', message);
};
```

## Configuration

Key environment variables:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Redis
REDIS_URL=redis://localhost:6379

# Security
RATE_LIMIT_REQUESTS_PER_MINUTE=60
ALLOWED_ORIGINS=["http://localhost:3000"]

# AI (optional)
OPENAI_API_KEY=your-openai-key

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Downgrade
alembic downgrade -1
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py

# Run integration tests
pytest -m integration
```

## Production Deployment

### Docker Compose (Recommended)

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Scale API instances
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

### Manual Deployment

1. **Set production environment variables**
2. **Use production WSGI server**
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```
3. **Set up reverse proxy (Nginx)**
4. **Configure SSL certificates**
5. **Set up monitoring and logging**

## Security Considerations

- Change default JWT secret key
- Use strong database passwords
- Enable SSL/TLS in production
- Configure firewall rules
- Regular security updates
- Monitor for suspicious activity
- Use environment variables for secrets
- Enable CORS only for trusted origins

## Monitoring & Logging

- Application logs: `logs/app.log`
- Error logs: `logs/error.log`
- Health endpoint: `/health`
- Structured logging with JSON format
- Performance monitoring
- Database query logging

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Documentation: https://docs.skema.app
- Issues: GitHub Issues
- Email: support@skema.app
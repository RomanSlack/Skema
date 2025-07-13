# Skema

[![Next.js](https://img.shields.io/badge/Next.js-15.2.0-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)](https://postgresql.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue?logo=typescript)](https://typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![Skema Screenshot](images/skema-hero.png)

A modern productivity platform that unifies task management, calendar scheduling, journaling, and AI-powered assistance into a single, elegant application.

[![Watch Demo](https://img.shields.io/badge/Watch%20Demo-YouTube-red?logo=youtube)](https://youtu.be/WxA-utyliIw)

## Tech Stack

**Frontend:** Next.js 15 + React 19 + TypeScript + Tailwind CSS  
**Backend:** FastAPI + SQLModel + PostgreSQL + Redis  
**AI Integration:** OpenAI GPT-4 + Serper Search API  
**Infrastructure:** Docker + Nginx + WebSocket support

## Features

### Core Applications
- **Quest Management**: Daily task tracking with completion status and due dates
- **Kanban Boards**: Visual project management with drag-and-drop functionality
- **Calendar Integration**: Schedule events with timezone-aware time management
- **Journal Entries**: Rich text journaling with mood tracking and search capabilities
- **AI Assistant**: Natural language interaction with intelligent task automation
- **Global Search**: Unified search across all content types with relevance scoring

### Technical Capabilities
- Real-time collaboration with WebSocket connections
- Responsive design with dark theme and custom color palettes
- Production-ready authentication and security measures
- Voice-enabled input with Whisper transcription
- Timezone conversion and Eastern Time defaults
- Comprehensive search functionality across all data types

## Development Setup

### Prerequisites
- Docker & Docker Compose
- Git
- Node.js 18+ and Python 3.11+ (for local development)

### Quick Start

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd Skema
   cp .env.example .env
   ```

2. **Start with Docker**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Local Development

**Frontend:**
```bash
cd Frontend
npm install
npm run dev
```

**Backend:**
```bash
cd Backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Application Overview

### Main Features

**Dashboard**
- Daily quest tracking with completion status
- Upcoming calendar events with Eastern Time display
- Recent journal entries and mood tracking
- Voice-enabled quick add functionality

**Quest Management**
- Create and track daily tasks
- Set due dates and times
- Mark items complete with visual feedback
- Search and filter quest history

**Calendar**
- Multiple view modes (month, week, day)
- Timezone-aware event creation and display
- Event editing and deletion capabilities
- Integration with AI for natural language scheduling

**Journal**
- Rich text entries with mood tracking
- Tag-based organization and search
- Date-based filtering and navigation
- Export and backup capabilities

**Search**
- Global search across all content types
- Filter by content type (quests, events, journal entries, boards)
- Relevance-based result ranking
- Quick access to any stored information

## API Documentation

### Core Endpoints

**Authentication**
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User authentication
- `GET /api/auth/me` - Current user information

**Quest Management**
- `GET /api/quest` - List user quests
- `POST /api/quest` - Create new quest
- `PUT /api/quest/{id}` - Update quest status

**Calendar**
- `GET /api/calendar/events` - List calendar events
- `POST /api/calendar/events` - Create new event
- `PUT /api/calendar/events/{id}` - Update event

**Journal**
- `GET /api/journal/entries` - List journal entries
- `POST /api/journal/entries` - Create entry
- `GET /api/journal/search` - Search entries

**AI Integration**
- `POST /api/ai/conversation` - Process AI requests
- `POST /api/ai/transcribe` - Voice transcription

Complete API documentation: http://localhost:8000/docs

## Configuration

### Environment Variables

Key configuration options:

```bash
# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# AI Integration
OPENAI_API_KEY=your-openai-key
SERPER_API_KEY=your-serper-key

# Security
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost:5432/skema
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

Built for modern productivity workflows.
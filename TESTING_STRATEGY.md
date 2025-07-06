# Comprehensive Testing Strategy for Skema Productivity App

## Executive Summary

This document outlines a comprehensive testing strategy for the Skema productivity application, a full-stack productivity platform featuring Kanban boards, calendar management, journaling, and AI command functionality. The strategy addresses testing across all layers of the application stack with a focus on production readiness, performance, security, and accessibility.

## Application Architecture Overview

### Backend (FastAPI)
- **Framework**: FastAPI with SQLModel and Alembic
- **Database**: PostgreSQL with JSONB support
- **Authentication**: JWT with refresh tokens
- **Real-time**: WebSocket connections
- **API Endpoints**: 30+ endpoints across 5 modules (auth, boards, calendar, journal, AI)

### Frontend (Next.js 15)
- **Framework**: Next.js 15 with React 19
- **State Management**: Zustand + React Query
- **UI Components**: Custom components with Tailwind CSS
- **Real-time**: WebSocket integration
- **Features**: 13 pages with complex interactions

### Database
- **Engine**: PostgreSQL with UUID primary keys
- **Features**: JSONB storage, full-text search, audit logging
- **Performance**: Optimized indexes and RLS policies

## 1. Test Architecture & Framework Selection

### Testing Pyramid Strategy

```
    /\
   /  \     E2E Tests (5%)
  /____\    
 /      \   Integration Tests (25%)
/________\  
\        /  Unit Tests (70%)
 \______/   
```

### Framework Selection

#### Backend Testing
- **Unit Testing**: pytest with pytest-asyncio
- **Integration Testing**: pytest with testcontainers
- **API Testing**: httpx for async HTTP testing
- **Database Testing**: pytest-postgresql with fixtures
- **Load Testing**: locust for performance testing

#### Frontend Testing
- **Unit Testing**: Jest with React Testing Library
- **Component Testing**: Storybook with Chromatic
- **Integration Testing**: Testing Library with MSW
- **E2E Testing**: Playwright for cross-browser testing
- **Visual Testing**: Percy for visual regression

#### Database Testing
- **Schema Testing**: Custom pytest fixtures
- **Migration Testing**: Alembic test utilities
- **Performance Testing**: pgbench integration

### Test Environment Configuration

```yaml
# test-environments.yml
environments:
  unit:
    database: in-memory SQLite
    cache: fake-redis
    external_apis: mocked
  
  integration:
    database: testcontainers PostgreSQL
    cache: testcontainers Redis
    external_apis: stubbed
  
  e2e:
    database: dedicated test PostgreSQL
    cache: dedicated test Redis
    external_apis: staging/mock services
```

## 2. Backend Testing Strategy

### 2.1 Unit Testing Strategy

#### Core Business Logic Testing
```python
# tests/unit/test_board_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.models.board import Board
from app.services.board_service import BoardService

class TestBoardService:
    @pytest.fixture
    def board_service(self):
        return BoardService(db_session=Mock())
    
    @pytest.mark.asyncio
    async def test_create_board_with_valid_data(self, board_service):
        # Test board creation with valid data
        board_data = {
            "title": "Test Board",
            "description": "Test Description",
            "color": "#6366f1"
        }
        
        board_service.db_session.add = Mock()
        board_service.db_session.commit = AsyncMock()
        
        result = await board_service.create_board(board_data, user_id="test-user")
        
        assert result.title == "Test Board"
        assert result.user_id == "test-user"
        board_service.db_session.add.assert_called_once()
        board_service.db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_board_with_invalid_color(self, board_service):
        # Test validation for invalid color codes
        board_data = {
            "title": "Test Board",
            "color": "invalid-color"
        }
        
        with pytest.raises(ValueError, match="Invalid color format"):
            await board_service.create_board(board_data, user_id="test-user")
```

#### Authentication & Authorization Testing
```python
# tests/unit/test_auth_service.py
import pytest
from datetime import datetime, timedelta
from app.core.auth import AuthService, verify_token, create_access_token

class TestAuthService:
    @pytest.fixture
    def auth_service(self):
        return AuthService()
    
    def test_create_access_token(self):
        user_id = "test-user-123"
        token = create_access_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        payload = verify_token(token, "access")
        assert payload["sub"] == user_id
    
    def test_password_hashing(self, auth_service):
        password = "test-password-123"
        hashed = auth_service.hash_password(password)
        
        assert hashed != password
        assert auth_service.verify_password(password, hashed)
        assert not auth_service.verify_password("wrong-password", hashed)
```

#### Utility Functions Testing
```python
# tests/unit/test_utilities.py
import pytest
from app.utils.validation import validate_email, validate_uuid
from app.utils.date import format_date, parse_date

class TestValidationUtils:
    @pytest.mark.parametrize("email,expected", [
        ("valid@example.com", True),
        ("invalid-email", False),
        ("", False),
        ("@example.com", False),
        ("valid@", False),
    ])
    def test_validate_email(self, email, expected):
        assert validate_email(email) == expected
    
    def test_validate_uuid(self):
        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        invalid_uuid = "not-a-uuid"
        
        assert validate_uuid(valid_uuid) is True
        assert validate_uuid(invalid_uuid) is False
```

### 2.2 Integration Testing Strategy

#### API Endpoint Testing
```python
# tests/integration/test_board_api.py
import pytest
from httpx import AsyncClient
from app.main import app
from tests.fixtures import create_test_user, create_test_board

@pytest.mark.integration
class TestBoardAPI:
    @pytest.fixture
    async def client(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    async def authenticated_user(self, client):
        user_data = {
            "email": "test@example.com",
            "password": "testpass123",
            "username": "testuser"
        }
        
        # Register user
        await client.post("/api/auth/register", json=user_data)
        
        # Login and get token
        login_response = await client.post("/api/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        
        token = login_response.json()["access_token"]
        return {"token": token, "user_data": user_data}
    
    @pytest.mark.asyncio
    async def test_create_board(self, client, authenticated_user):
        headers = {"Authorization": f"Bearer {authenticated_user['token']}"}
        board_data = {
            "title": "Test Board",
            "description": "Integration test board",
            "color": "#6366f1"
        }
        
        response = await client.post("/api/boards", json=board_data, headers=headers)
        
        assert response.status_code == 201
        board = response.json()
        assert board["title"] == "Test Board"
        assert board["user_id"] is not None
    
    @pytest.mark.asyncio
    async def test_get_boards(self, client, authenticated_user):
        headers = {"Authorization": f"Bearer {authenticated_user['token']}"}
        
        # Create test boards
        for i in range(3):
            await client.post("/api/boards", json={
                "title": f"Board {i}",
                "description": f"Test board {i}"
            }, headers=headers)
        
        response = await client.get("/api/boards", headers=headers)
        
        assert response.status_code == 200
        boards = response.json()
        assert len(boards) == 3
        assert all(board["title"].startswith("Board") for board in boards)
```

#### Database Integration Testing
```python
# tests/integration/test_database.py
import pytest
from sqlmodel import Session, select
from app.models.user import User
from app.models.board import Board
from app.database import get_session

@pytest.mark.integration
class TestDatabaseIntegration:
    @pytest.fixture
    def db_session(self):
        session = next(get_session())
        try:
            yield session
        finally:
            session.close()
    
    @pytest.mark.asyncio
    async def test_user_board_relationship(self, db_session):
        # Create user
        user = User(
            email="test@example.com",
            hashed_password="hashed_password",
            username="testuser"
        )
        db_session.add(user)
        db_session.commit()
        
        # Create board for user
        board = Board(
            title="Test Board",
            user_id=user.id,
            description="Test board description"
        )
        db_session.add(board)
        db_session.commit()
        
        # Verify relationship
        retrieved_user = db_session.get(User, user.id)
        assert len(retrieved_user.boards) == 1
        assert retrieved_user.boards[0].title == "Test Board"
```

### 2.3 WebSocket Testing Strategy

```python
# tests/integration/test_websocket.py
import pytest
import json
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.integration
class TestWebSocket:
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_websocket_connection(self, client):
        # Create authenticated user and get token
        token = self.get_auth_token(client)
        
        with client.websocket_connect(f"/ws?token={token}") as websocket:
            # Test connection established
            assert websocket is not None
            
            # Send test message
            test_message = {
                "type": "board_update",
                "data": {"board_id": "test-board", "action": "create_card"}
            }
            websocket.send_text(json.dumps(test_message))
            
            # Receive response
            response = websocket.receive_text()
            response_data = json.loads(response)
            
            assert response_data["type"] == "acknowledgment"
    
    def get_auth_token(self, client):
        # Helper method to get authentication token
        user_data = {
            "email": "test@example.com",
            "password": "testpass123"
        }
        response = client.post("/api/auth/login", json=user_data)
        return response.json()["access_token"]
```

### 2.4 Performance Testing Strategy

```python
# tests/performance/test_api_performance.py
import pytest
import asyncio
import time
from httpx import AsyncClient
from app.main import app

@pytest.mark.performance
class TestAPIPerformance:
    @pytest.mark.asyncio
    async def test_board_creation_performance(self):
        """Test that board creation completes within 200ms"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Setup authenticated user
            token = await self.get_auth_token(client)
            headers = {"Authorization": f"Bearer {token}"}
            
            board_data = {
                "title": "Performance Test Board",
                "description": "Testing API performance"
            }
            
            start_time = time.time()
            response = await client.post("/api/boards", json=board_data, headers=headers)
            end_time = time.time()
            
            assert response.status_code == 201
            assert (end_time - start_time) < 0.2  # 200ms threshold
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            token = await self.get_auth_token(client)
            headers = {"Authorization": f"Bearer {token}"}
            
            # Create 10 concurrent requests
            tasks = []
            for i in range(10):
                task = client.post("/api/boards", json={
                    "title": f"Concurrent Board {i}",
                    "description": f"Concurrent test {i}"
                }, headers=headers)
                tasks.append(task)
            
            start_time = time.time()
            responses = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # All requests should succeed
            assert all(response.status_code == 201 for response in responses)
            # Total time should be reasonable
            assert (end_time - start_time) < 2.0  # 2 second threshold
```

## 3. Frontend Testing Strategy

### 3.1 Component Testing Strategy

#### React Component Testing
```typescript
// tests/components/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '@/components/ui/Button';

describe('Button Component', () => {
  test('renders button with correct text', () => {
    render(<Button>Click me</Button>);
    
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
  });
  
  test('calls onClick handler when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    const button = screen.getByRole('button');
    fireEvent.click(button);
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
  
  test('applies correct CSS classes for variants', () => {
    const { rerender } = render(<Button variant="primary">Primary</Button>);
    
    expect(screen.getByRole('button')).toHaveClass('btn-primary');
    
    rerender(<Button variant="secondary">Secondary</Button>);
    expect(screen.getByRole('button')).toHaveClass('btn-secondary');
  });
  
  test('is disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>);
    
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });
});
```

#### Complex Component Testing
```typescript
// tests/components/BoardCard.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BoardCard } from '@/components/boards/BoardCard';
import { mockBoard } from '@/tests/mocks/board';

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
};

describe('BoardCard Component', () => {
  const mockBoardData = mockBoard({
    id: 'test-board-1',
    title: 'Test Board',
    description: 'Test Description',
    color: '#6366f1',
  });
  
  test('renders board information correctly', () => {
    renderWithProviders(<BoardCard board={mockBoardData} />);
    
    expect(screen.getByText('Test Board')).toBeInTheDocument();
    expect(screen.getByText('Test Description')).toBeInTheDocument();
  });
  
  test('handles drag and drop', async () => {
    const handleDragEnd = jest.fn();
    
    renderWithProviders(
      <DragDropContext onDragEnd={handleDragEnd}>
        <BoardCard board={mockBoardData} />
      </DragDropContext>
    );
    
    const card = screen.getByTestId('board-card');
    
    // Simulate drag start
    fireEvent.dragStart(card);
    
    // Simulate drop
    fireEvent.dragEnd(card);
    
    await waitFor(() => {
      expect(handleDragEnd).toHaveBeenCalled();
    });
  });
});
```

### 3.2 Page Integration Testing

```typescript
// tests/pages/Dashboard.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { Dashboard } from '@/app/dashboard/page';
import { setupMSW } from '@/tests/mocks/server';
import { mockDashboardStats } from '@/tests/mocks/dashboard';

// Setup MSW for API mocking
setupMSW();

describe('Dashboard Page', () => {
  beforeEach(() => {
    // Mock authentication
    jest.spyOn(require('@/lib/stores/auth'), 'useAuthStore').mockReturnValue({
      user: {
        id: 'test-user',
        email: 'test@example.com',
        username: 'testuser',
      },
      isAuthenticated: true,
    });
  });
  
  test('loads and displays dashboard data', async () => {
    render(<Dashboard />);
    
    // Check loading state
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    
    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('Total Boards')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument(); // Mocked value
    });
    
    // Check all dashboard sections are present
    expect(screen.getByText('Recent Activity')).toBeInTheDocument();
    expect(screen.getByText('Upcoming Events')).toBeInTheDocument();
    expect(screen.getByText('Recent Journal Entries')).toBeInTheDocument();
  });
  
  test('handles API error gracefully', async () => {
    // Mock API error
    server.use(
      rest.get('/api/dashboard/stats', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ error: 'Server error' }));
      })
    );
    
    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText(/error loading dashboard/i)).toBeInTheDocument();
    });
  });
});
```

### 3.3 State Management Testing

```typescript
// tests/stores/authStore.test.ts
import { act, renderHook } from '@testing-library/react';
import { useAuthStore } from '@/lib/stores/auth';
import { mockUser } from '@/tests/mocks/user';

describe('Auth Store', () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.getState().reset();
  });
  
  test('login sets user and authentication state', () => {
    const { result } = renderHook(() => useAuthStore());
    
    act(() => {
      result.current.login(mockUser, 'access-token', 'refresh-token');
    });
    
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.accessToken).toBe('access-token');
  });
  
  test('logout clears user and authentication state', () => {
    const { result } = renderHook(() => useAuthStore());
    
    // First login
    act(() => {
      result.current.login(mockUser, 'access-token', 'refresh-token');
    });
    
    // Then logout
    act(() => {
      result.current.logout();
    });
    
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.accessToken).toBeNull();
  });
  
  test('token refresh updates tokens', () => {
    const { result } = renderHook(() => useAuthStore());
    
    act(() => {
      result.current.login(mockUser, 'old-token', 'refresh-token');
    });
    
    act(() => {
      result.current.setTokens('new-token', 'new-refresh-token');
    });
    
    expect(result.current.accessToken).toBe('new-token');
    expect(result.current.refreshToken).toBe('new-refresh-token');
  });
});
```

### 3.4 Real-time Features Testing

```typescript
// tests/integration/websocket.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { WebSocketProvider } from '@/lib/contexts/WebSocketContext';
import { BoardsPage } from '@/app/boards/page';
import { mockWebSocket } from '@/tests/mocks/websocket';

describe('WebSocket Integration', () => {
  test('receives real-time board updates', async () => {
    const mockWS = mockWebSocket();
    
    render(
      <WebSocketProvider>
        <BoardsPage />
      </WebSocketProvider>
    );
    
    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('My Boards')).toBeInTheDocument();
    });
    
    // Simulate incoming WebSocket message
    act(() => {
      mockWS.simulateMessage({
        type: 'board_update',
        data: {
          board_id: 'test-board',
          action: 'create',
          board: {
            id: 'test-board',
            title: 'New Board',
            description: 'Created in real-time',
          }
        }
      });
    });
    
    // Check that new board appears
    await waitFor(() => {
      expect(screen.getByText('New Board')).toBeInTheDocument();
    });
  });
});
```

## 4. End-to-End Testing Strategy

### 4.1 User Journey Testing

```typescript
// tests/e2e/user-journey.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Complete User Journey', () => {
  test('user can register, login, and create a board', async ({ page }) => {
    // Navigate to landing page
    await page.goto('/');
    
    // Register new user
    await page.click('text=Get Started');
    await page.fill('[data-testid="email"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'testpass123');
    await page.fill('[data-testid="username"]', 'testuser');
    await page.fill('[data-testid="firstName"]', 'Test');
    await page.fill('[data-testid="lastName"]', 'User');
    await page.click('button[type="submit"]');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('h1')).toContainText('Welcome, Test');
    
    // Navigate to boards
    await page.click('text=Boards');
    await expect(page).toHaveURL('/boards');
    
    // Create new board
    await page.click('text=Create Board');
    await page.fill('[data-testid="board-title"]', 'My Test Board');
    await page.fill('[data-testid="board-description"]', 'This is a test board');
    await page.click('button[type="submit"]');
    
    // Verify board was created
    await expect(page.locator('[data-testid="board-card"]')).toContainText('My Test Board');
    
    // Open board and add a card
    await page.click('[data-testid="board-card"]');
    await page.click('text=Add Card');
    await page.fill('[data-testid="card-title"]', 'Test Card');
    await page.fill('[data-testid="card-description"]', 'This is a test card');
    await page.click('button[type="submit"]');
    
    // Verify card was created
    await expect(page.locator('[data-testid="card"]')).toContainText('Test Card');
  });
  
  test('user can manage calendar events', async ({ page }) => {
    // Login as existing user
    await page.goto('/auth/login');
    await page.fill('[data-testid="email"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    
    // Navigate to calendar
    await page.click('text=Calendar');
    await expect(page).toHaveURL('/calendar');
    
    // Create new event
    await page.click('text=New Event');
    await page.fill('[data-testid="event-title"]', 'Test Meeting');
    await page.fill('[data-testid="event-description"]', 'Important meeting');
    await page.click('[data-testid="start-date"]');
    await page.click('text=Today');
    await page.click('[data-testid="start-time"]');
    await page.selectOption('[data-testid="start-time"]', '10:00');
    await page.click('button[type="submit"]');
    
    // Verify event was created
    await expect(page.locator('[data-testid="calendar-event"]')).toContainText('Test Meeting');
  });
});
```

### 4.2 Cross-Browser Testing

```typescript
// tests/e2e/cross-browser.spec.ts
import { test, expect, devices } from '@playwright/test';

const browsers = ['chromium', 'firefox', 'webkit'];
const devices_list = [
  devices['Desktop Chrome'],
  devices['Desktop Firefox'],
  devices['Desktop Safari'],
  devices['iPhone 12'],
  devices['Pixel 5'],
];

for (const device of devices_list) {
  test.describe(`Cross-browser testing - ${device.name}`, () => {
    test.use({ ...device });
    
    test('core functionality works across browsers', async ({ page }) => {
      await page.goto('/');
      
      // Test responsive design
      if (device.name.includes('iPhone') || device.name.includes('Pixel')) {
        // Mobile-specific tests
        await page.click('[data-testid="mobile-menu-toggle"]');
        await expect(page.locator('[data-testid="mobile-menu"]')).toBeVisible();
      }
      
      // Test core functionality
      await page.click('text=Get Started');
      await expect(page).toHaveURL('/auth/register');
      
      // Test form interactions
      await page.fill('[data-testid="email"]', 'test@example.com');
      await page.fill('[data-testid="password"]', 'testpass123');
      
      // Verify form validation
      await expect(page.locator('[data-testid="email"]')).toHaveValue('test@example.com');
    });
  });
}
```

### 4.3 Performance Testing

```typescript
// tests/e2e/performance.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Performance Tests', () => {
  test('page load performance', async ({ page }) => {
    // Start performance monitoring
    await page.goto('/dashboard');
    
    // Measure Core Web Vitals
    const metrics = await page.evaluate(() => {
      return new Promise((resolve) => {
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          const metrics = {};
          
          entries.forEach((entry) => {
            if (entry.entryType === 'largest-contentful-paint') {
              metrics.lcp = entry.startTime;
            }
            if (entry.entryType === 'first-input') {
              metrics.fid = entry.processingStart - entry.startTime;
            }
            if (entry.entryType === 'layout-shift') {
              metrics.cls = entry.value;
            }
          });
          
          resolve(metrics);
        }).observe({ entryTypes: ['largest-contentful-paint', 'first-input', 'layout-shift'] });
      });
    });
    
    // Assert performance thresholds
    expect(metrics.lcp).toBeLessThan(2500); // LCP < 2.5s
    expect(metrics.fid).toBeLessThan(100);   // FID < 100ms
    expect(metrics.cls).toBeLessThan(0.1);   // CLS < 0.1
  });
  
  test('API response times', async ({ page }) => {
    // Monitor network requests
    const responses = [];
    
    page.on('response', (response) => {
      if (response.url().includes('/api/')) {
        responses.push({
          url: response.url(),
          status: response.status(),
          timing: response.timing(),
        });
      }
    });
    
    await page.goto('/dashboard');
    
    // Wait for all API calls to complete
    await page.waitForLoadState('networkidle');
    
    // Assert API response times
    for (const response of responses) {
      expect(response.timing.responseEnd - response.timing.requestStart).toBeLessThan(200);
    }
  });
});
```

## 5. Database Testing Strategy

### 5.1 Schema Validation Testing

```python
# tests/database/test_schema.py
import pytest
from sqlalchemy import inspect, text
from app.database import engine
from app.models import *

@pytest.mark.integration
class TestDatabaseSchema:
    @pytest.mark.asyncio
    async def test_all_tables_exist(self):
        """Verify all required tables exist"""
        expected_tables = [
            'users', 'boards', 'cards', 'calendar_events',
            'journal_entries', 'ai_commands', 'user_sessions', 'audit_logs'
        ]
        
        async with engine.connect() as conn:
            inspector = inspect(conn)
            existing_tables = inspector.get_table_names()
            
            for table in expected_tables:
                assert table in existing_tables, f"Table {table} not found"
    
    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self):
        """Test foreign key relationships"""
        async with engine.connect() as conn:
            inspector = inspect(conn)
            
            # Test boards -> users relationship
            boards_fks = inspector.get_foreign_keys('boards')
            user_fk = next((fk for fk in boards_fks if fk['referred_table'] == 'users'), None)
            assert user_fk is not None
            assert 'user_id' in user_fk['constrained_columns']
            
            # Test cards -> boards relationship
            cards_fks = inspector.get_foreign_keys('cards')
            board_fk = next((fk for fk in cards_fks if fk['referred_table'] == 'boards'), None)
            assert board_fk is not None
            assert 'board_id' in board_fk['constrained_columns']
    
    @pytest.mark.asyncio
    async def test_indexes_exist(self):
        """Verify performance indexes exist"""
        async with engine.connect() as conn:
            inspector = inspect(conn)
            
            # Check users table indexes
            users_indexes = inspector.get_indexes('users')
            index_names = [idx['name'] for idx in users_indexes]
            assert 'idx_users_email' in index_names
            
            # Check boards table indexes
            boards_indexes = inspector.get_indexes('boards')
            index_names = [idx['name'] for idx in boards_indexes]
            assert 'idx_boards_user_id' in index_names
```

### 5.2 JSONB Functionality Testing

```python
# tests/database/test_jsonb.py
import pytest
from sqlalchemy import text
from app.database import engine

@pytest.mark.integration
class TestJSONBFunctionality:
    @pytest.mark.asyncio
    async def test_user_preferences_jsonb(self):
        """Test JSONB operations on user preferences"""
        async with engine.connect() as conn:
            # Insert user with preferences
            await conn.execute(text("""
                INSERT INTO users (email, hashed_password, preferences)
                VALUES ('test@example.com', 'hashed', '{"theme": "dark", "notifications": {"email": true}}')
            """))
            
            # Query JSONB data
            result = await conn.execute(text("""
                SELECT preferences->>'theme' as theme,
                       preferences->'notifications'->>'email' as email_notifications
                FROM users WHERE email = 'test@example.com'
            """))
            
            row = result.fetchone()
            assert row[0] == 'dark'
            assert row[1] == 'true'
            
            # Update JSONB data
            await conn.execute(text("""
                UPDATE users 
                SET preferences = jsonb_set(preferences, '{theme}', '"light"')
                WHERE email = 'test@example.com'
            """))
            
            # Verify update
            result = await conn.execute(text("""
                SELECT preferences->>'theme' FROM users WHERE email = 'test@example.com'
            """))
            
            row = result.fetchone()
            assert row[0] == 'light'
    
    @pytest.mark.asyncio
    async def test_board_settings_jsonb(self):
        """Test JSONB operations on board settings"""
        async with engine.connect() as conn:
            # Create test user first
            user_result = await conn.execute(text("""
                INSERT INTO users (email, hashed_password)
                VALUES ('board_test@example.com', 'hashed')
                RETURNING id
            """))
            user_id = user_result.fetchone()[0]
            
            # Insert board with complex settings
            await conn.execute(text("""
                INSERT INTO boards (user_id, title, settings)
                VALUES (:user_id, 'Test Board', :settings)
            """), {
                'user_id': user_id,
                'settings': {
                    'columns': [
                        {'id': 'todo', 'title': 'To Do', 'color': '#ef4444'},
                        {'id': 'done', 'title': 'Done', 'color': '#10b981'}
                    ],
                    'automation': {'auto_archive': True}
                }
            })
            
            # Query nested JSONB
            result = await conn.execute(text("""
                SELECT settings->'automation'->>'auto_archive' as auto_archive,
                       jsonb_array_length(settings->'columns') as column_count
                FROM boards WHERE title = 'Test Board'
            """))
            
            row = result.fetchone()
            assert row[0] == 'true'
            assert row[1] == 2
```

### 5.3 Migration Testing

```python
# tests/database/test_migrations.py
import pytest
from alembic import command
from alembic.config import Config
from app.database import engine

@pytest.mark.integration
class TestMigrations:
    @pytest.fixture
    def alembic_config(self):
        config = Config("alembic.ini")
        config.set_main_option("script_location", "migrations")
        return config
    
    @pytest.mark.asyncio
    async def test_migrations_up_and_down(self, alembic_config):
        """Test migration up and down operations"""
        # Start from clean database
        command.downgrade(alembic_config, "base")
        
        # Apply all migrations
        command.upgrade(alembic_config, "head")
        
        # Verify tables exist
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]
            
            expected_tables = ['users', 'boards', 'cards', 'calendar_events']
            for table in expected_tables:
                assert table in tables
        
        # Test downgrade
        command.downgrade(alembic_config, "base")
        
        # Verify tables are removed
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]
            
            # Only alembic_version should remain
            assert len(tables) <= 1
```

### 5.4 Performance Testing

```python
# tests/database/test_performance.py
import pytest
import time
from sqlalchemy import text
from app.database import engine

@pytest.mark.performance
class TestDatabasePerformance:
    @pytest.mark.asyncio
    async def test_query_performance(self):
        """Test that queries execute within acceptable time limits"""
        async with engine.connect() as conn:
            # Create test data
            await self.create_test_data(conn, 1000)  # 1000 boards
            
            # Test board listing query performance
            start_time = time.time()
            
            result = await conn.execute(text("""
                SELECT b.id, b.title, b.created_at,
                       COUNT(c.id) as card_count
                FROM boards b
                LEFT JOIN cards c ON b.id = c.board_id
                WHERE b.user_id = :user_id
                GROUP BY b.id, b.title, b.created_at
                ORDER BY b.created_at DESC
                LIMIT 20
            """), {'user_id': 'test-user-id'})
            
            results = result.fetchall()
            end_time = time.time()
            
            # Should complete within 50ms
            assert (end_time - start_time) < 0.05
            assert len(results) == 20
    
    @pytest.mark.asyncio
    async def test_full_text_search_performance(self):
        """Test full-text search performance"""
        async with engine.connect() as conn:
            # Create searchable content
            await self.create_searchable_content(conn, 10000)
            
            start_time = time.time()
            
            result = await conn.execute(text("""
                SELECT title, ts_rank(to_tsvector('english', title), query) as rank
                FROM cards, to_tsquery('english', 'test & important') query
                WHERE to_tsvector('english', title) @@ query
                ORDER BY rank DESC
                LIMIT 10
            """))
            
            results = result.fetchall()
            end_time = time.time()
            
            # Should complete within 100ms
            assert (end_time - start_time) < 0.1
            assert len(results) > 0
    
    async def create_test_data(self, conn, count):
        """Helper to create test data"""
        # Implementation for creating test data
        pass
    
    async def create_searchable_content(self, conn, count):
        """Helper to create searchable content"""
        # Implementation for creating searchable content
        pass
```

## 6. Security Testing Strategy

### 6.1 Authentication Testing

```python
# tests/security/test_authentication.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.security
class TestAuthentication:
    @pytest.fixture
    async def client(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_requires_auth(self, client):
        """Test that protected endpoints require authentication"""
        response = await client.get("/api/boards")
        assert response.status_code == 401
        
        response = await client.post("/api/boards", json={"title": "Test"})
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, client):
        """Test that invalid tokens are rejected"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = await client.get("/api/boards", headers=headers)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_expired_token_rejected(self, client):
        """Test that expired tokens are rejected"""
        # Create expired token
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJleHAiOjE2MzQ5MzQzMDB9.invalid"
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = await client.get("/api/boards", headers=headers)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_password_hashing_security(self, client):
        """Test password hashing security"""
        user_data = {
            "email": "security@example.com",
            "password": "test-password-123",
            "username": "securityuser"
        }
        
        response = await client.post("/api/auth/register", json=user_data)
        assert response.status_code == 201
        
        # Verify password is hashed (not stored in plain text)
        from app.database import get_session
        from app.models.user import User
        from sqlalchemy import select
        
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.email == user_data["email"])
            )
            user = result.scalar_one_or_none()
            
            assert user is not None
            assert user.hashed_password != user_data["password"]
            assert user.hashed_password.startswith("$2b$")  # bcrypt hash
```

### 6.2 Authorization Testing

```python
# tests/security/test_authorization.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.security
class TestAuthorization:
    @pytest.fixture
    async def authenticated_users(self, client):
        """Create two authenticated users for testing"""
        # Create user 1
        user1_data = {
            "email": "user1@example.com",
            "password": "password123",
            "username": "user1"
        }
        await client.post("/api/auth/register", json=user1_data)
        login1_response = await client.post("/api/auth/login", json={
            "email": user1_data["email"],
            "password": user1_data["password"]
        })
        user1_token = login1_response.json()["access_token"]
        
        # Create user 2
        user2_data = {
            "email": "user2@example.com",
            "password": "password123",
            "username": "user2"
        }
        await client.post("/api/auth/register", json=user2_data)
        login2_response = await client.post("/api/auth/login", json={
            "email": user2_data["email"],
            "password": user2_data["password"]
        })
        user2_token = login2_response.json()["access_token"]
        
        return {
            "user1": {"token": user1_token, "data": user1_data},
            "user2": {"token": user2_token, "data": user2_data}
        }
    
    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_boards(self, client, authenticated_users):
        """Test that users cannot access other users' boards"""
        user1_headers = {"Authorization": f"Bearer {authenticated_users['user1']['token']}"}
        user2_headers = {"Authorization": f"Bearer {authenticated_users['user2']['token']}"}
        
        # User 1 creates a board
        board_data = {"title": "User 1 Board", "description": "Private board"}
        response = await client.post("/api/boards", json=board_data, headers=user1_headers)
        assert response.status_code == 201
        board_id = response.json()["id"]
        
        # User 2 tries to access User 1's board
        response = await client.get(f"/api/boards/{board_id}", headers=user2_headers)
        assert response.status_code == 403  # Forbidden
    
    @pytest.mark.asyncio
    async def test_user_cannot_modify_other_users_data(self, client, authenticated_users):
        """Test that users cannot modify other users' data"""
        user1_headers = {"Authorization": f"Bearer {authenticated_users['user1']['token']}"}
        user2_headers = {"Authorization": f"Bearer {authenticated_users['user2']['token']}"}
        
        # User 1 creates a board
        board_data = {"title": "User 1 Board"}
        response = await client.post("/api/boards", json=board_data, headers=user1_headers)
        board_id = response.json()["id"]
        
        # User 2 tries to modify User 1's board
        update_data = {"title": "Hacked Board"}
        response = await client.put(f"/api/boards/{board_id}", json=update_data, headers=user2_headers)
        assert response.status_code == 403
        
        # User 2 tries to delete User 1's board
        response = await client.delete(f"/api/boards/{board_id}", headers=user2_headers)
        assert response.status_code == 403
```

### 6.3 Input Validation Testing

```python
# tests/security/test_input_validation.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.security
class TestInputValidation:
    @pytest.fixture
    async def authenticated_client(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Register and login user
            user_data = {
                "email": "test@example.com",
                "password": "testpass123",
                "username": "testuser"
            }
            await client.post("/api/auth/register", json=user_data)
            login_response = await client.post("/api/auth/login", json={
                "email": user_data["email"],
                "password": user_data["password"]
            })
            token = login_response.json()["access_token"]
            client.headers.update({"Authorization": f"Bearer {token}"})
            yield client
    
    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, authenticated_client):
        """Test SQL injection prevention"""
        # Attempt SQL injection in board title
        malicious_data = {
            "title": "'; DROP TABLE users; --",
            "description": "SQL injection attempt"
        }
        
        response = await authenticated_client.post("/api/boards", json=malicious_data)
        # Should either succeed with sanitized data or fail validation
        assert response.status_code in [201, 400]
        
        # Verify users table still exists by making another request
        response = await authenticated_client.get("/api/boards")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_xss_prevention(self, authenticated_client):
        """Test XSS prevention"""
        # Attempt XSS in board description
        malicious_data = {
            "title": "Test Board",
            "description": "<script>alert('XSS')</script>"
        }
        
        response = await authenticated_client.post("/api/boards", json=malicious_data)
        assert response.status_code == 201
        
        # Verify script tags are sanitized
        board = response.json()
        assert "<script>" not in board["description"]
        assert "alert" not in board["description"]
    
    @pytest.mark.asyncio
    async def test_oversized_input_rejection(self, authenticated_client):
        """Test rejection of oversized inputs"""
        # Test with oversized title (assuming max 255 chars)
        oversized_data = {
            "title": "A" * 1000,  # 1000 characters
            "description": "Test description"
        }
        
        response = await authenticated_client.post("/api/boards", json=oversized_data)
        assert response.status_code == 400
        
        error_response = response.json()
        assert "title" in error_response["detail"]
    
    @pytest.mark.asyncio
    async def test_invalid_email_format_rejection(self, authenticated_client):
        """Test rejection of invalid email formats"""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user@invalid",
            "",
            "user name@example.com"
        ]
        
        for email in invalid_emails:
            user_data = {
                "email": email,
                "password": "testpass123",
                "username": "testuser"
            }
            
            response = await authenticated_client.post("/api/auth/register", json=user_data)
            assert response.status_code == 400
```

### 6.4 Rate Limiting Testing

```python
# tests/security/test_rate_limiting.py
import pytest
import asyncio
from httpx import AsyncClient
from app.main import app

@pytest.mark.security
class TestRateLimiting:
    @pytest.fixture
    async def client(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_login_rate_limiting(self, client):
        """Test rate limiting on login endpoint"""
        login_data = {
            "email": "test@example.com",
            "password": "wrongpassword"
        }
        
        # Make rapid login attempts
        tasks = []
        for _ in range(10):
            task = client.post("/api/auth/login", json=login_data)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Some requests should be rate limited
        rate_limited_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 429)
        assert rate_limited_count > 0
    
    @pytest.mark.asyncio
    async def test_api_rate_limiting(self, client):
        """Test rate limiting on API endpoints"""
        # Register and login user
        user_data = {
            "email": "ratelimit@example.com",
            "password": "testpass123",
            "username": "ratelimituser"
        }
        await client.post("/api/auth/register", json=user_data)
        login_response = await client.post("/api/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Make rapid API requests
        tasks = []
        for i in range(50):
            task = client.post("/api/boards", json={
                "title": f"Rate Limit Test {i}"
            }, headers=headers)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Some requests should be rate limited
        rate_limited_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 429)
        assert rate_limited_count > 0
```

## 7. Performance Testing Strategy

### 7.1 Load Testing

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import random
import json

class SkemaUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Register and login user"""
        self.username = f"user{random.randint(1000, 9999)}"
        self.email = f"{self.username}@example.com"
        self.password = "testpass123"
        
        # Register
        self.client.post("/api/auth/register", json={
            "email": self.email,
            "password": self.password,
            "username": self.username,
            "first_name": "Test",
            "last_name": "User"
        })
        
        # Login
        response = self.client.post("/api/auth/login", json={
            "email": self.email,
            "password": self.password
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Create initial board
        self.create_initial_board()
    
    def create_initial_board(self):
        """Create initial board for testing"""
        response = self.client.post("/api/boards", json={
            "title": f"{self.username}'s Board",
            "description": "Load testing board"
        })
        if response.status_code == 201:
            self.board_id = response.json()["id"]
    
    @task(3)
    def get_boards(self):
        """Get user's boards"""
        self.client.get("/api/boards")
    
    @task(2)
    def create_board(self):
        """Create new board"""
        self.client.post("/api/boards", json={
            "title": f"Board {random.randint(1, 1000)}",
            "description": "Load test board"
        })
    
    @task(4)
    def get_board_details(self):
        """Get specific board details"""
        if hasattr(self, 'board_id'):
            self.client.get(f"/api/boards/{self.board_id}")
    
    @task(2)
    def create_card(self):
        """Create card in board"""
        if hasattr(self, 'board_id'):
            self.client.post(f"/api/boards/{self.board_id}/cards", json={
                "title": f"Card {random.randint(1, 1000)}",
                "description": "Load test card"
            })
    
    @task(1)
    def get_calendar_events(self):
        """Get calendar events"""
        self.client.get("/api/calendar/events")
    
    @task(1)
    def create_calendar_event(self):
        """Create calendar event"""
        self.client.post("/api/calendar/events", json={
            "title": f"Event {random.randint(1, 1000)}",
            "description": "Load test event",
            "start_datetime": "2024-01-15T10:00:00Z",
            "end_datetime": "2024-01-15T11:00:00Z"
        })
    
    @task(1)
    def get_journal_entries(self):
        """Get journal entries"""
        self.client.get("/api/journal/entries")
    
    @task(1)
    def create_journal_entry(self):
        """Create journal entry"""
        self.client.post("/api/journal/entries", json={
            "title": f"Entry {random.randint(1, 1000)}",
            "content": "This is a load test journal entry with some content to test the system.",
            "entry_date": "2024-01-15"
        })
```

### 7.2 Stress Testing

```python
# tests/performance/test_stress.py
import pytest
import asyncio
import aiohttp
from datetime import datetime

@pytest.mark.performance
class TestStress:
    @pytest.mark.asyncio
    async def test_concurrent_user_creation(self):
        """Test system under concurrent user creation load"""
        async def create_user(session, user_id):
            user_data = {
                "email": f"stress{user_id}@example.com",
                "password": "testpass123",
                "username": f"stress{user_id}",
                "first_name": "Stress",
                "last_name": "Test"
            }
            
            async with session.post("/api/auth/register", json=user_data) as response:
                return response.status
        
        # Create 100 concurrent users
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(100):
                task = create_user(session, i)
                tasks.append(task)
            
            start_time = datetime.now()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = datetime.now()
            
            # Analyze results
            success_count = sum(1 for r in results if r == 201)
            duration = (end_time - start_time).total_seconds()
            
            # Assert reasonable performance
            assert success_count >= 90  # At least 90% success rate
            assert duration < 30  # Complete within 30 seconds
    
    @pytest.mark.asyncio
    async def test_database_connection_pool(self):
        """Test database connection pool under load"""
        async def make_db_request(session, token):
            headers = {"Authorization": f"Bearer {token}"}
            async with session.get("/api/boards", headers=headers) as response:
                return response.status
        
        # Create authenticated user
        async with aiohttp.ClientSession() as session:
            # Register and login
            user_data = {
                "email": "dbtest@example.com",
                "password": "testpass123",
                "username": "dbtest"
            }
            
            await session.post("/api/auth/register", json=user_data)
            async with session.post("/api/auth/login", json={
                "email": user_data["email"],
                "password": user_data["password"]
            }) as response:
                login_data = await response.json()
                token = login_data["access_token"]
            
            # Make 200 concurrent database requests
            tasks = []
            for _ in range(200):
                task = make_db_request(session, token)
                tasks.append(task)
            
            start_time = datetime.now()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = datetime.now()
            
            # Analyze results
            success_count = sum(1 for r in results if r == 200)
            duration = (end_time - start_time).total_seconds()
            
            # Assert system handles load
            assert success_count >= 190  # At least 95% success rate
            assert duration < 10  # Complete within 10 seconds
```

### 7.3 Memory and Resource Testing

```python
# tests/performance/test_memory.py
import pytest
import psutil
import gc
from app.main import app
from httpx import AsyncClient

@pytest.mark.performance
class TestMemoryUsage:
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self):
        """Test for memory leaks during normal operation"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Register user
            user_data = {
                "email": "memory@example.com",
                "password": "testpass123",
                "username": "memoryuser"
            }
            await client.post("/api/auth/register", json=user_data)
            
            # Login
            login_response = await client.post("/api/auth/login", json={
                "email": user_data["email"],
                "password": user_data["password"]
            })
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Perform many operations
            for i in range(1000):
                await client.post("/api/boards", json={
                    "title": f"Memory Test Board {i}",
                    "description": "Testing memory usage"
                }, headers=headers)
                
                await client.get("/api/boards", headers=headers)
                
                if i % 100 == 0:
                    # Force garbage collection
                    gc.collect()
        
        # Check final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024  # 100MB
    
    @pytest.mark.asyncio
    async def test_database_connection_cleanup(self):
        """Test that database connections are properly cleaned up"""
        from app.database import engine
        
        initial_pool_size = engine.pool.size()
        checked_out_connections = engine.pool.checkedout()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make multiple requests
            for _ in range(50):
                await client.get("/health")
        
        # Check connection pool after requests
        final_pool_size = engine.pool.size()
        final_checked_out = engine.pool.checkedout()
        
        # Connections should be returned to pool
        assert final_checked_out == checked_out_connections
        assert final_pool_size == initial_pool_size
```

## 8. Accessibility Testing Strategy

### 8.1 Automated Accessibility Testing

```typescript
// tests/accessibility/axe.test.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility Tests', () => {
  test('dashboard page meets WCAG 2.1 AA standards', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Run axe accessibility scan
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    
    expect(accessibilityScanResults.violations).toEqual([]);
  });
  
  test('boards page accessibility', async ({ page }) => {
    // Login first
    await page.goto('/auth/login');
    await page.fill('[data-testid="email"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    
    // Navigate to boards
    await page.goto('/boards');
    await page.waitForLoadState('networkidle');
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    
    expect(accessibilityScanResults.violations).toEqual([]);
  });
  
  test('calendar page accessibility', async ({ page }) => {
    // Login and navigate to calendar
    await page.goto('/auth/login');
    await page.fill('[data-testid="email"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    
    await page.goto('/calendar');
    await page.waitForLoadState('networkidle');
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    
    expect(accessibilityScanResults.violations).toEqual([]);
  });
});
```

### 8.2 Keyboard Navigation Testing

```typescript
// tests/accessibility/keyboard.test.ts
import { test, expect } from '@playwright/test';

test.describe('Keyboard Navigation', () => {
  test('can navigate entire app using only keyboard', async ({ page }) => {
    await page.goto('/');
    
    // Test landing page navigation
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toContainText('Get Started');
    
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL('/auth/register');
    
    // Test form navigation
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toHaveAttribute('data-testid', 'email');
    
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toHaveAttribute('data-testid', 'password');
    
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toHaveAttribute('data-testid', 'username');
    
    // Test form submission
    await page.fill('[data-testid="email"]', 'keyboard@example.com');
    await page.fill('[data-testid="password"]', 'testpass123');
    await page.fill('[data-testid="username"]', 'keyboarduser');
    await page.fill('[data-testid="firstName"]', 'Keyboard');
    await page.fill('[data-testid="lastName"]', 'User');
    
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toHaveAttribute('type', 'submit');
    
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL('/dashboard');
  });
  
  test('keyboard shortcuts work correctly', async ({ page }) => {
    // Login first
    await page.goto('/auth/login');
    await page.fill('[data-testid="email"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    
    // Test global keyboard shortcuts
    await page.keyboard.press('Alt+1');
    await expect(page).toHaveURL('/dashboard');
    
    await page.keyboard.press('Alt+2');
    await expect(page).toHaveURL('/boards');
    
    await page.keyboard.press('Alt+3');
    await expect(page).toHaveURL('/calendar');
    
    // Test AI command bar shortcut
    await page.keyboard.press('Control+k');
    await expect(page.locator('[data-testid="ai-command-bar"]')).toBeVisible();
    
    await page.keyboard.press('Escape');
    await expect(page.locator('[data-testid="ai-command-bar"]')).not.toBeVisible();
  });
  
  test('modal and dialog keyboard trapping', async ({ page }) => {
    // Login and navigate to boards
    await page.goto('/auth/login');
    await page.fill('[data-testid="email"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    
    await page.goto('/boards');
    
    // Open create board modal
    await page.click('text=Create Board');
    await expect(page.locator('[data-testid="create-board-modal"]')).toBeVisible();
    
    // Test focus trap
    await page.keyboard.press('Tab');
    const firstFocusableElement = page.locator(':focus');
    
    // Tab through all elements and ensure focus stays within modal
    const focusableElements = await page.locator('[data-testid="create-board-modal"] input, [data-testid="create-board-modal"] button, [data-testid="create-board-modal"] textarea').count();
    
    for (let i = 0; i < focusableElements + 1; i++) {
      await page.keyboard.press('Tab');
    }
    
    // Focus should cycle back to first element
    await expect(page.locator(':focus')).toBe(firstFocusableElement);
    
    // Test escape key closes modal
    await page.keyboard.press('Escape');
    await expect(page.locator('[data-testid="create-board-modal"]')).not.toBeVisible();
  });
});
```

### 8.3 Screen Reader Testing

```typescript
// tests/accessibility/screen-reader.test.ts
import { test, expect } from '@playwright/test';

test.describe('Screen Reader Compatibility', () => {
  test('proper ARIA labels and roles', async ({ page }) => {
    await page.goto('/boards');
    
    // Check main navigation has proper ARIA labels
    await expect(page.locator('nav')).toHaveAttribute('aria-label', 'Main navigation');
    
    // Check board cards have proper ARIA labels
    const boardCards = page.locator('[data-testid="board-card"]');
    await expect(boardCards.first()).toHaveAttribute('role', 'button');
    await expect(boardCards.first()).toHaveAttribute('aria-label');
    
    // Check interactive elements have proper labels
    await expect(page.locator('button[data-testid="create-board"]')).toHaveAttribute('aria-label', 'Create new board');
    
    // Check form elements have proper labels
    await page.click('text=Create Board');
    await expect(page.locator('input[data-testid="board-title"]')).toHaveAttribute('aria-label', 'Board title');
    await expect(page.locator('textarea[data-testid="board-description"]')).toHaveAttribute('aria-label', 'Board description');
  });
  
  test('proper heading structure', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Check proper heading hierarchy
    const h1 = page.locator('h1');
    await expect(h1).toBeVisible();
    await expect(h1).toContainText('Dashboard');
    
    const h2Elements = page.locator('h2');
    const h2Count = await h2Elements.count();
    expect(h2Count).toBeGreaterThan(0);
    
    // Verify no heading levels are skipped
    const headings = await page.locator('h1, h2, h3, h4, h5, h6').allTextContents();
    // Implementation to verify proper heading hierarchy
  });
  
  test('live regions for dynamic content', async ({ page }) => {
    await page.goto('/boards');
    
    // Check for aria-live regions
    await expect(page.locator('[aria-live="polite"]')).toBeVisible();
    
    // Test that notifications appear in live regions
    await page.click('[data-testid="create-board"]');
    await page.fill('[data-testid="board-title"]', 'Test Board');
    await page.click('button[type="submit"]');
    
    // Check that success message appears in live region
    await expect(page.locator('[aria-live="polite"]')).toContainText('Board created successfully');
  });
});
```

### 8.4 Color Contrast Testing

```typescript
// tests/accessibility/color-contrast.test.ts
import { test, expect } from '@playwright/test';

test.describe('Color Contrast', () => {
  test('text meets WCAG AA contrast ratios', async ({ page }) => {
    await page.goto('/');
    
    // Check primary text contrast
    const primaryText = page.locator('h1').first();
    const textColor = await primaryText.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return styles.color;
    });
    
    const backgroundColor = await primaryText.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return styles.backgroundColor;
    });
    
    // Use contrast calculation library to verify ratio
    const contrastRatio = calculateContrastRatio(textColor, backgroundColor);
    expect(contrastRatio).toBeGreaterThan(4.5); // WCAG AA standard
  });
  
  test('button states have sufficient contrast', async ({ page }) => {
    await page.goto('/auth/login');
    
    const button = page.locator('button[type="submit"]');
    
    // Test normal state
    let buttonColor = await button.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return styles.color;
    });
    
    let buttonBg = await button.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return styles.backgroundColor;
    });
    
    expect(calculateContrastRatio(buttonColor, buttonBg)).toBeGreaterThan(4.5);
    
    // Test hover state
    await button.hover();
    buttonColor = await button.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return styles.color;
    });
    
    buttonBg = await button.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return styles.backgroundColor;
    });
    
    expect(calculateContrastRatio(buttonColor, buttonBg)).toBeGreaterThan(4.5);
  });
});

function calculateContrastRatio(color1: string, color2: string): number {
  // Implementation of WCAG contrast ratio calculation
  // This would use a library like 'color-contrast' or custom implementation
  return 4.6; // Placeholder
}
```

## 9. Test Data Management Strategy

### 9.1 Test Data Factory

```python
# tests/factories/user_factory.py
import factory
from factory import fuzzy
from datetime import datetime, timedelta
from app.models.user import User

class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    id = factory.Faker('uuid4')
    email = factory.Faker('email')
    username = factory.Faker('user_name')
    hashed_password = factory.Faker('sha256')
    full_name = factory.Faker('name')
    is_active = True
    email_verified = True
    created_at = factory.Faker('date_time_this_year', before_now=True)
    updated_at = factory.LazyAttribute(lambda obj: obj.created_at)
    
    preferences = factory.Dict({
        'theme': factory.Faker('random_element', elements=['light', 'dark']),
        'notifications': factory.Dict({
            'email': factory.Faker('boolean'),
            'push': factory.Faker('boolean'),
            'board_updates': factory.Faker('boolean'),
            'calendar_reminders': factory.Faker('boolean')
        }),
        'dashboard': factory.Dict({
            'layout': 'default',
            'widgets': ['boards', 'calendar', 'journal', 'recent_activity']
        })
    })

# tests/factories/board_factory.py
import factory
from factory import fuzzy
from app.models.board import Board
from tests.factories.user_factory import UserFactory

class BoardFactory(factory.Factory):
    class Meta:
        model = Board
    
    id = factory.Faker('uuid4')
    user = factory.SubFactory(UserFactory)
    title = factory.Faker('sentence', nb_words=3)
    description = factory.Faker('text', max_nb_chars=200)
    color = factory.Faker('hex_color')
    is_archived = False
    created_at = factory.Faker('date_time_this_year', before_now=True)
    updated_at = factory.LazyAttribute(lambda obj: obj.created_at)
    
    settings = factory.Dict({
        'columns': [
            {'id': 'todo', 'title': 'To Do', 'color': '#ef4444'},
            {'id': 'in_progress', 'title': 'In Progress', 'color': '#f59e0b'},
            {'id': 'done', 'title': 'Done', 'color': '#10b981'}
        ],
        'automation': {
            'auto_archive': factory.Faker('boolean'),
            'move_completed_cards': factory.Faker('boolean')
        },
        'permissions': {
            'public': False,
            'collaborators': []
        }
    })

# tests/factories/card_factory.py
import factory
from app.models.card import Card
from tests.factories.board_factory import BoardFactory

class CardFactory(factory.Factory):
    class Meta:
        model = Card
    
    id = factory.Faker('uuid4')
    board = factory.SubFactory(BoardFactory)
    title = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('text', max_nb_chars=500)
    status = factory.Faker('random_element', elements=['todo', 'in_progress', 'done'])
    priority = factory.Faker('random_element', elements=['low', 'medium', 'high'])
    position = factory.Faker('random_int', min=0, max=100)
    created_at = factory.Faker('date_time_this_year', before_now=True)
    updated_at = factory.LazyAttribute(lambda obj: obj.created_at)
    
    metadata = factory.Dict({
        'tags': factory.Faker('words', nb=3),
        'due_date': factory.Faker('date_time_this_year', after_now=True),
        'checklist': [],
        'attachments': [],
        'assigned_to': None,
        'estimated_hours': factory.Faker('random_int', min=1, max=8),
        'actual_hours': None
    })
```

### 9.2 Test Database Management

```python
# tests/conftest.py
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_session
from app.main import app

# Test database URL
TEST_DATABASE_URL = "postgresql://test:test@localhost/test_skema"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    """Create test database"""
    engine = create_engine(TEST_DATABASE_URL)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Drop all tables
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
async def db_session(test_db):
    """Create a database session for testing"""
    TestingSessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=test_db
    )
    
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def override_get_session(db_session):
    """Override the get_session dependency"""
    def _get_session():
        return db_session
    
    app.dependency_overrides[get_session] = _get_session
    yield
    app.dependency_overrides.clear()
```

### 9.3 Test Data Seeding

```python
# tests/utils/seed_data.py
import asyncio
from sqlalchemy.orm import Session
from tests.factories.user_factory import UserFactory
from tests.factories.board_factory import BoardFactory
from tests.factories.card_factory import CardFactory

async def seed_test_data(session: Session, scenario: str = "default"):
    """Seed test data based on scenario"""
    
    if scenario == "default":
        # Create 5 users
        users = UserFactory.create_batch(5)
        session.add_all(users)
        
        # Create 10 boards (2 per user)
        boards = []
        for user in users:
            user_boards = BoardFactory.create_batch(2, user=user)
            boards.extend(user_boards)
        session.add_all(boards)
        
        # Create 30 cards (3 per board)
        cards = []
        for board in boards:
            board_cards = CardFactory.create_batch(3, board=board)
            cards.extend(board_cards)
        session.add_all(cards)
        
        session.commit()
        
    elif scenario == "performance":
        # Create large dataset for performance testing
        users = UserFactory.create_batch(100)
        session.add_all(users)
        
        boards = []
        for user in users:
            user_boards = BoardFactory.create_batch(10, user=user)
            boards.extend(user_boards)
        session.add_all(boards)
        
        cards = []
        for board in boards:
            board_cards = CardFactory.create_batch(20, board=board)
            cards.extend(board_cards)
        session.add_all(cards)
        
        session.commit()
        
    elif scenario == "edge_cases":
        # Create edge case data
        # User with no boards
        user_no_boards = UserFactory.create(username="no_boards_user")
        session.add(user_no_boards)
        
        # User with many boards
        user_many_boards = UserFactory.create(username="many_boards_user")
        many_boards = BoardFactory.create_batch(50, user=user_many_boards)
        session.add_all([user_many_boards] + many_boards)
        
        # Board with no cards
        user_empty_board = UserFactory.create(username="empty_board_user")
        empty_board = BoardFactory.create(user=user_empty_board, title="Empty Board")
        session.add_all([user_empty_board, empty_board])
        
        session.commit()
```

## 10. CI/CD Integration Strategy

### 10.1 GitHub Actions Configuration

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_skema
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd Backend
        pip install -r requirements.txt
        pip install -e ".[dev]"
    
    - name: Run linting
      run: |
        cd Backend
        flake8 app tests
        black --check app tests
        isort --check-only app tests
    
    - name: Run type checking
      run: |
        cd Backend
        mypy app
    
    - name: Run unit tests
      run: |
        cd Backend
        pytest tests/unit -v --cov=app --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_skema
        REDIS_URL: redis://localhost:6379
    
    - name: Run integration tests
      run: |
        cd Backend
        pytest tests/integration -v --cov=app --cov-report=xml --cov-append
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_skema
        REDIS_URL: redis://localhost:6379
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./Backend/coverage.xml
        flags: backend

  frontend-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: Frontend/package-lock.json
    
    - name: Install dependencies
      run: |
        cd Frontend
        npm ci
    
    - name: Run linting
      run: |
        cd Frontend
        npm run lint
    
    - name: Run type checking
      run: |
        cd Frontend
        npm run typecheck
    
    - name: Run unit tests
      run: |
        cd Frontend
        npm run test:unit -- --coverage
    
    - name: Run component tests
      run: |
        cd Frontend
        npm run test:components -- --coverage
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./Frontend/coverage/lcov.info
        flags: frontend

  e2e-tests:
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_skema
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: Frontend/package-lock.json
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install backend dependencies
      run: |
        cd Backend
        pip install -r requirements.txt
    
    - name: Install frontend dependencies
      run: |
        cd Frontend
        npm ci
    
    - name: Start backend server
      run: |
        cd Backend
        uvicorn app.main:app --host 0.0.0.0 --port 8000 &
        sleep 10
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_skema
    
    - name: Build frontend
      run: |
        cd Frontend
        npm run build
    
    - name: Start frontend server
      run: |
        cd Frontend
        npm start &
        sleep 10
    
    - name: Install Playwright
      run: |
        cd Frontend
        npx playwright install
    
    - name: Run E2E tests
      run: |
        cd Frontend
        npx playwright test
    
    - name: Upload E2E test results
      uses: actions/upload-artifact@v3
      if: failure()
      with:
        name: playwright-report
        path: Frontend/playwright-report/

  performance-tests:
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]
    if: github.event_name == 'pull_request'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd Backend
        pip install -r requirements.txt
        pip install locust
    
    - name: Run performance tests
      run: |
        cd Backend
        locust --headless --users 10 --spawn-rate 2 --run-time 60s --host http://localhost:8000
    
    - name: Upload performance report
      uses: actions/upload-artifact@v3
      with:
        name: performance-report
        path: Backend/performance-report.html

  security-tests:
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Run Bandit security scan
      run: |
        cd Backend
        pip install bandit
        bandit -r app -f json -o bandit-report.json
    
    - name: Run npm audit
      run: |
        cd Frontend
        npm audit --audit-level high
    
    - name: Upload security reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          Backend/bandit-report.json
          Frontend/npm-audit-report.json

  accessibility-tests:
    runs-on: ubuntu-latest
    needs: [frontend-tests]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: Frontend/package-lock.json
    
    - name: Install dependencies
      run: |
        cd Frontend
        npm ci
    
    - name: Run accessibility tests
      run: |
        cd Frontend
        npm run test:accessibility
    
    - name: Upload accessibility report
      uses: actions/upload-artifact@v3
      with:
        name: accessibility-report
        path: Frontend/accessibility-report.html
```

### 10.2 Quality Gates

```yaml
# .github/workflows/quality-gates.yml
name: Quality Gates

on:
  pull_request:
    branches: [ main ]

jobs:
  quality-checks:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Check code coverage
      run: |
        # Backend coverage should be > 80%
        backend_coverage=$(grep -oP '(?<=<coverage line-rate=")[^"]*' Backend/coverage.xml)
        if (( $(echo "$backend_coverage < 0.8" | bc -l) )); then
          echo "Backend coverage $backend_coverage is below 80%"
          exit 1
        fi
        
        # Frontend coverage should be > 80%
        frontend_coverage=$(grep -oP '(?<=<coverage line-rate=")[^"]*' Frontend/coverage.xml)
        if (( $(echo "$frontend_coverage < 0.8" | bc -l) )); then
          echo "Frontend coverage $frontend_coverage is below 80%"
          exit 1
        fi
    
    - name: Check performance benchmarks
      run: |
        # API response time should be < 200ms
        # Database query time should be < 50ms
        # Frontend load time should be < 3s
        # Implementation depends on performance test results
        echo "Performance benchmarks check"
    
    - name: Check security vulnerabilities
      run: |
        # No high or critical vulnerabilities allowed
        # Implementation depends on security scan results
        echo "Security vulnerabilities check"
    
    - name: Check accessibility compliance
      run: |
        # No accessibility violations allowed
        # Implementation depends on accessibility test results
        echo "Accessibility compliance check"
```

### 10.3 Test Reporting

```python
# tests/utils/reporter.py
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Any

class TestReporter:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'summary': {},
            'details': {}
        }
    
    def add_test_suite_result(self, suite_name: str, results: Dict[str, Any]):
        """Add results from a test suite"""
        self.results['details'][suite_name] = results
        
        # Update summary
        if 'summary' not in self.results:
            self.results['summary'] = {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'duration': 0
            }
        
        self.results['summary']['total_tests'] += results.get('total', 0)
        self.results['summary']['passed'] += results.get('passed', 0)
        self.results['summary']['failed'] += results.get('failed', 0)
        self.results['summary']['skipped'] += results.get('skipped', 0)
        self.results['summary']['duration'] += results.get('duration', 0)
    
    def generate_html_report(self, output_path: str):
        """Generate HTML test report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Skema Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .test-suite {{ margin: 20px 0; border: 1px solid #ddd; }}
                .test-suite h3 {{ background: #4CAF50; color: white; padding: 10px; margin: 0; }}
                .test-case {{ padding: 10px; border-bottom: 1px solid #eee; }}
                .passed {{ color: #4CAF50; }}
                .failed {{ color: #f44336; }}
                .skipped {{ color: #ff9800; }}
            </style>
        </head>
        <body>
            <h1>Skema Test Report</h1>
            
            <div class="summary">
                <h2>Summary</h2>
                <p>Total Tests: {self.results['summary']['total_tests']}</p>
                <p class="passed">Passed: {self.results['summary']['passed']}</p>
                <p class="failed">Failed: {self.results['summary']['failed']}</p>
                <p class="skipped">Skipped: {self.results['summary']['skipped']}</p>
                <p>Duration: {self.results['summary']['duration']:.2f}s</p>
            </div>
            
            <div class="test-suites">
                <h2>Test Suites</h2>
        """
        
        for suite_name, suite_results in self.results['details'].items():
            html_content += f"""
                <div class="test-suite">
                    <h3>{suite_name}</h3>
                    <div class="test-cases">
            """
            
            for test_case in suite_results.get('test_cases', []):
                status_class = test_case['status'].lower()
                html_content += f"""
                    <div class="test-case {status_class}">
                        <strong>{test_case['name']}</strong> - {test_case['status']}
                        {f"<br>Error: {test_case['error']}" if test_case.get('error') else ""}
                    </div>
                """
            
            html_content += """
                    </div>
                </div>
            """
        
        html_content += """
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html_content)
    
    def generate_json_report(self, output_path: str):
        """Generate JSON test report"""
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
    
    def generate_junit_xml(self, output_path: str):
        """Generate JUnit XML report"""
        root = ET.Element('testsuites')
        
        for suite_name, suite_results in self.results['details'].items():
            suite_elem = ET.SubElement(root, 'testsuite')
            suite_elem.set('name', suite_name)
            suite_elem.set('tests', str(suite_results.get('total', 0)))
            suite_elem.set('failures', str(suite_results.get('failed', 0)))
            suite_elem.set('skipped', str(suite_results.get('skipped', 0)))
            suite_elem.set('time', str(suite_results.get('duration', 0)))
            
            for test_case in suite_results.get('test_cases', []):
                case_elem = ET.SubElement(suite_elem, 'testcase')
                case_elem.set('name', test_case['name'])
                case_elem.set('time', str(test_case.get('duration', 0)))
                
                if test_case['status'] == 'FAILED':
                    failure_elem = ET.SubElement(case_elem, 'failure')
                    failure_elem.text = test_case.get('error', '')
                elif test_case['status'] == 'SKIPPED':
                    ET.SubElement(case_elem, 'skipped')
        
        tree = ET.ElementTree(root)
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
```

## 11. Monitoring and Alerts

### 11.1 Test Execution Monitoring

```python
# tests/monitoring/test_monitor.py
import time
import psutil
import logging
from datetime import datetime
from typing import Dict, List

class TestExecutionMonitor:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.metrics = {}
        self.alerts = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def start_monitoring(self):
        """Start monitoring test execution"""
        self.start_time = datetime.now()
        self.metrics['start_time'] = self.start_time.isoformat()
        
        # Initial system metrics
        self.metrics['initial_memory'] = psutil.virtual_memory().percent
        self.metrics['initial_cpu'] = psutil.cpu_percent()
        
        self.logger.info(f"Test monitoring started at {self.start_time}")
    
    def record_test_result(self, test_name: str, result: str, duration: float):
        """Record individual test result"""
        if 'test_results' not in self.metrics:
            self.metrics['test_results'] = []
        
        self.metrics['test_results'].append({
            'test_name': test_name,
            'result': result,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        })
        
        # Check for performance alerts
        if duration > 10.0:  # 10 second threshold
            self.alerts.append({
                'type': 'SLOW_TEST',
                'message': f"Test {test_name} took {duration:.2f}s",
                'severity': 'WARNING'
            })
    
    def check_system_resources(self):
        """Check system resource usage"""
        memory_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent()
        
        if memory_percent > 90:
            self.alerts.append({
                'type': 'HIGH_MEMORY',
                'message': f"Memory usage at {memory_percent}%",
                'severity': 'CRITICAL'
            })
        
        if cpu_percent > 90:
            self.alerts.append({
                'type': 'HIGH_CPU',
                'message': f"CPU usage at {cpu_percent}%",
                'severity': 'CRITICAL'
            })
    
    def end_monitoring(self):
        """End monitoring and generate report"""
        self.end_time = datetime.now()
        self.metrics['end_time'] = self.end_time.isoformat()
        self.metrics['total_duration'] = (self.end_time - self.start_time).total_seconds()
        
        # Final system metrics
        self.metrics['final_memory'] = psutil.virtual_memory().percent
        self.metrics['final_cpu'] = psutil.cpu_percent()
        
        # Generate summary
        self.generate_summary()
        
        self.logger.info(f"Test monitoring ended at {self.end_time}")
        
        return self.metrics
    
    def generate_summary(self):
        """Generate test execution summary"""
        if 'test_results' not in self.metrics:
            return
        
        results = self.metrics['test_results']
        
        self.metrics['summary'] = {
            'total_tests': len(results),
            'passed': len([r for r in results if r['result'] == 'PASSED']),
            'failed': len([r for r in results if r['result'] == 'FAILED']),
            'skipped': len([r for r in results if r['result'] == 'SKIPPED']),
            'average_duration': sum(r['duration'] for r in results) / len(results),
            'max_duration': max(r['duration'] for r in results),
            'min_duration': min(r['duration'] for r in results),
            'alerts': self.alerts
        }
```

### 11.2 Performance Metrics Collection

```python
# tests/monitoring/performance_monitor.py
import time
import requests
from datetime import datetime
from typing import Dict, List

class PerformanceMonitor:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.metrics = []
        self.thresholds = {
            'api_response_time': 200,  # milliseconds
            'database_query_time': 50,  # milliseconds
            'memory_usage': 90,  # percentage
            'error_rate': 5  # percentage
        }
    
    def measure_api_response_time(self, endpoint: str, method: str = 'GET', **kwargs):
        """Measure API response time"""
        start_time = time.time()
        
        try:
            response = requests.request(method, f"{self.base_url}{endpoint}", **kwargs)
            end_time = time.time()
            
            duration_ms = (end_time - start_time) * 1000
            
            metric = {
                'timestamp': datetime.now().isoformat(),
                'type': 'API_RESPONSE_TIME',
                'endpoint': endpoint,
                'method': method,
                'duration_ms': duration_ms,
                'status_code': response.status_code,
                'success': response.status_code < 400
            }
            
            self.metrics.append(metric)
            
            # Check threshold
            if duration_ms > self.thresholds['api_response_time']:
                self.alert(
                    'API_SLOW_RESPONSE',
                    f"API {endpoint} took {duration_ms:.2f}ms",
                    'WARNING'
                )
            
            return metric
            
        except Exception as e:
            self.alert(
                'API_ERROR',
                f"API {endpoint} failed: {str(e)}",
                'CRITICAL'
            )
            return None
    
    def measure_database_performance(self, query: str, connection):
        """Measure database query performance"""
        start_time = time.time()
        
        try:
            connection.execute(query)
            end_time = time.time()
            
            duration_ms = (end_time - start_time) * 1000
            
            metric = {
                'timestamp': datetime.now().isoformat(),
                'type': 'DATABASE_QUERY_TIME',
                'query': query[:100],  # Truncate for logging
                'duration_ms': duration_ms,
                'success': True
            }
            
            self.metrics.append(metric)
            
            # Check threshold
            if duration_ms > self.thresholds['database_query_time']:
                self.alert(
                    'DATABASE_SLOW_QUERY',
                    f"Database query took {duration_ms:.2f}ms",
                    'WARNING'
                )
            
            return metric
            
        except Exception as e:
            self.alert(
                'DATABASE_ERROR',
                f"Database query failed: {str(e)}",
                'CRITICAL'
            )
            return None
    
    def alert(self, alert_type: str, message: str, severity: str):
        """Generate alert"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'message': message,
            'severity': severity
        }
        
        # In production, this would send to monitoring service
        print(f"ALERT [{severity}]: {message}")
        
        return alert
    
    def generate_performance_report(self) -> Dict:
        """Generate performance report"""
        if not self.metrics:
            return {}
        
        api_metrics = [m for m in self.metrics if m['type'] == 'API_RESPONSE_TIME']
        db_metrics = [m for m in self.metrics if m['type'] == 'DATABASE_QUERY_TIME']
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_api_calls': len(api_metrics),
                'total_db_queries': len(db_metrics),
                'average_api_response_time': sum(m['duration_ms'] for m in api_metrics) / len(api_metrics) if api_metrics else 0,
                'average_db_query_time': sum(m['duration_ms'] for m in db_metrics) / len(db_metrics) if db_metrics else 0,
                'api_success_rate': len([m for m in api_metrics if m['success']]) / len(api_metrics) * 100 if api_metrics else 0,
                'db_success_rate': len([m for m in db_metrics if m['success']]) / len(db_metrics) * 100 if db_metrics else 0,
            },
            'details': {
                'api_metrics': api_metrics,
                'database_metrics': db_metrics
            }
        }
        
        return report
```

## 12. Test Coverage and Quality Metrics

### 12.1 Coverage Configuration

```python
# tests/coverage/coverage_config.py
COVERAGE_CONFIG = {
    'source': ['app'],
    'omit': [
        '*/tests/*',
        '*/migrations/*',
        '*/venv/*',
        '*/env/*',
        '*/node_modules/*',
        '*/coverage/*'
    ],
    'exclude_lines': [
        'pragma: no cover',
        'def __repr__',
        'if self.debug:',
        'if settings.DEBUG',
        'raise AssertionError',
        'raise NotImplementedError',
        'if 0:',
        'if __name__ == .__main__.:'
    ],
    'precision': 2,
    'show_missing': True,
    'skip_covered': False,
    'minimum_coverage': {
        'backend': 80,
        'frontend': 80,
        'e2e': 70
    }
}
```

### 12.2 Quality Metrics Dashboard

```python
# tests/quality/metrics_dashboard.py
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List

class QualityMetricsDashboard:
    def __init__(self, db_path: str = "quality_metrics.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize metrics database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                branch TEXT,
                commit_hash TEXT,
                test_suite TEXT,
                total_tests INTEGER,
                passed INTEGER,
                failed INTEGER,
                skipped INTEGER,
                duration REAL,
                coverage_percentage REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                test_run_id INTEGER,
                metric_type TEXT,
                metric_name TEXT,
                value REAL,
                unit TEXT,
                FOREIGN KEY (test_run_id) REFERENCES test_runs (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def record_test_run(self, run_data: Dict) -> int:
        """Record a test run"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO test_runs (
                timestamp, branch, commit_hash, test_suite,
                total_tests, passed, failed, skipped,
                duration, coverage_percentage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            run_data['timestamp'],
            run_data['branch'],
            run_data['commit_hash'],
            run_data['test_suite'],
            run_data['total_tests'],
            run_data['passed'],
            run_data['failed'],
            run_data['skipped'],
            run_data['duration'],
            run_data['coverage_percentage']
        ))
        
        run_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return run_id
    
    def record_performance_metric(self, run_id: int, metric_type: str, 
                                 metric_name: str, value: float, unit: str):
        """Record a performance metric"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO performance_metrics (
                timestamp, test_run_id, metric_type, metric_name, value, unit
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            run_id,
            metric_type,
            metric_name,
            value,
            unit
        ))
        
        conn.commit()
        conn.close()
    
    def get_test_trend(self, days: int = 30) -> Dict:
        """Get test trend for the last N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
            SELECT 
                DATE(timestamp) as date,
                AVG(coverage_percentage) as avg_coverage,
                SUM(passed) as total_passed,
                SUM(failed) as total_failed,
                AVG(duration) as avg_duration
            FROM test_runs
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        ''', (since_date.isoformat(),))
        
        results = cursor.fetchall()
        conn.close()
        
        return {
            'dates': [row[0] for row in results],
            'coverage': [row[1] for row in results],
            'passed': [row[2] for row in results],
            'failed': [row[3] for row in results],
            'duration': [row[4] for row in results]
        }
    
    def get_performance_trend(self, metric_type: str, days: int = 30) -> Dict:
        """Get performance trend for specific metric type"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
            SELECT 
                DATE(pm.timestamp) as date,
                pm.metric_name,
                AVG(pm.value) as avg_value,
                pm.unit
            FROM performance_metrics pm
            JOIN test_runs tr ON pm.test_run_id = tr.id
            WHERE pm.metric_type = ? AND pm.timestamp >= ?
            GROUP BY DATE(pm.timestamp), pm.metric_name
            ORDER BY date
        ''', (metric_type, since_date.isoformat()))
        
        results = cursor.fetchall()
        conn.close()
        
        # Group by metric name
        metrics = {}
        for row in results:
            date, metric_name, avg_value, unit = row
            if metric_name not in metrics:
                metrics[metric_name] = {
                    'dates': [],
                    'values': [],
                    'unit': unit
                }
            metrics[metric_name]['dates'].append(date)
            metrics[metric_name]['values'].append(avg_value)
        
        return metrics
    
    def generate_quality_report(self) -> Dict:
        """Generate comprehensive quality report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get latest test run
        cursor.execute('''
            SELECT * FROM test_runs
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        latest_run = cursor.fetchone()
        
        # Get coverage trend
        cursor.execute('''
            SELECT AVG(coverage_percentage) as avg_coverage
            FROM test_runs
            WHERE timestamp >= ?
        ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
        weekly_coverage = cursor.fetchone()[0]
        
        # Get failure rate
        cursor.execute('''
            SELECT 
                SUM(failed) as total_failed,
                SUM(total_tests) as total_tests
            FROM test_runs
            WHERE timestamp >= ?
        ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
        failure_stats = cursor.fetchone()
        failure_rate = (failure_stats[0] / failure_stats[1]) * 100 if failure_stats[1] > 0 else 0
        
        conn.close()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'latest_run': {
                'timestamp': latest_run[1] if latest_run else None,
                'coverage': latest_run[10] if latest_run else None,
                'passed': latest_run[5] if latest_run else None,
                'failed': latest_run[6] if latest_run else None,
                'duration': latest_run[9] if latest_run else None
            },
            'weekly_stats': {
                'average_coverage': weekly_coverage,
                'failure_rate': failure_rate
            },
            'quality_score': self.calculate_quality_score(weekly_coverage, failure_rate)
        }
    
    def calculate_quality_score(self, coverage: float, failure_rate: float) -> float:
        """Calculate overall quality score"""
        if coverage is None or failure_rate is None:
            return 0.0
        
        # Score based on coverage (0-50 points)
        coverage_score = min(50, (coverage / 100) * 50)
        
        # Score based on failure rate (0-30 points)
        failure_score = max(0, 30 - (failure_rate * 6))
        
        # Performance score (0-20 points) - placeholder
        performance_score = 15  # Would be calculated from actual performance metrics
        
        return coverage_score + failure_score + performance_score
```

## 13. Conclusion and Implementation Roadmap

### 13.1 Implementation Phases

#### Phase 1: Foundation (Weeks 1-2)
- Set up basic testing infrastructure
- Implement unit testing frameworks
- Configure CI/CD pipeline
- Basic test data management

#### Phase 2: Core Testing (Weeks 3-4)
- Complete unit test coverage
- Implement API integration tests
- Set up database testing
- Basic performance testing

#### Phase 3: Advanced Testing (Weeks 5-6)
- E2E testing with Playwright
- Security testing implementation
- Accessibility testing setup
- WebSocket testing

#### Phase 4: Quality Assurance (Weeks 7-8)
- Performance optimization
- Security hardening
- Accessibility compliance
- Test coverage improvement

#### Phase 5: Monitoring & Reporting (Weeks 9-10)
- Monitoring dashboard
- Quality metrics tracking
- Performance alerts
- Comprehensive reporting

### 13.2 Success Metrics

#### Technical Metrics
- **Code Coverage**: >80% for both backend and frontend
- **Test Execution Time**: <10 minutes for full suite
- **API Response Time**: <200ms for 95% of requests
- **Database Query Time**: <50ms for 95% of queries
- **Security Vulnerabilities**: Zero high/critical issues
- **Accessibility Compliance**: WCAG 2.1 AA standard

#### Quality Metrics
- **Test Reliability**: >99% consistent results
- **Bug Detection Rate**: >90% of bugs caught in testing
- **Production Defect Rate**: <1% escape rate
- **Performance Regression**: Zero performance degradation
- **User Experience**: Zero accessibility barriers

### 13.3 Risk Mitigation

#### Technical Risks
- **Flaky Tests**: Implement retry mechanisms and better test isolation
- **Performance Bottlenecks**: Continuous performance monitoring
- **Security Vulnerabilities**: Regular security scanning and updates
- **Accessibility Issues**: Automated accessibility testing in CI/CD

#### Process Risks
- **Test Maintenance**: Automated test generation and maintenance tools
- **Team Adoption**: Comprehensive training and documentation
- **CI/CD Reliability**: Redundant testing environments
- **Resource Constraints**: Parallel test execution and optimization

### 13.4 Maintenance Strategy

#### Continuous Improvement
- Monthly test suite review and optimization
- Quarterly security assessments
- Regular performance benchmark updates
- Accessibility standard compliance reviews

#### Tool Updates
- Framework and dependency updates
- Security tool updates
- Performance monitoring tool updates
- Accessibility tool updates

This comprehensive testing strategy ensures that the Skema productivity application meets the highest standards of quality, performance, security, and accessibility while maintaining efficient development workflows and continuous delivery capabilities.

---

**Document Version**: 1.0  
**Last Updated**: December 2024  
**Next Review**: March 2025

# ADR-001: Database Architecture for Skema Productivity App

## Status
Accepted

## Context
We need to design a database schema for a production-ready productivity application that supports:
- Kanban-style boards with cards
- Calendar events with recurring patterns
- Journal entries with rich content
- AI command history and analytics
- User authentication and preferences
- Real-time collaboration features

## Decision
We have chosen PostgreSQL 15+ with JSONB columns for flexible data storage, following these key principles:

### 1. **Hybrid Relational-Document Model**
- **Relational** for core entities and relationships (users, boards, cards, events)
- **JSONB** for metadata, preferences, and flexible content that may evolve
- **Best of both worlds**: ACID compliance with NoSQL flexibility

### 2. **Core Table Structure**
```sql
users           # Authentication and user profiles
boards          # Kanban boards (1:many with users)
cards           # Kanban cards (1:many with boards)
calendar_events # Calendar events (1:many with users)
journal_entries # Journal entries (1:many with users)
ai_commands     # AI command history (1:many with users)
user_sessions   # JWT session management
audit_logs      # Security and compliance logging
```

### 3. **JSONB Usage Strategy**
- **User preferences**: Theme, notifications, dashboard layout
- **Board settings**: Column configurations, automation rules
- **Card metadata**: Tags, due dates, checklists, attachments
- **Calendar metadata**: Recurrence rules, attendees, reminders
- **Journal metadata**: Weather, location, custom fields
- **AI metadata**: Model details, token usage, confidence scores

### 4. **Performance Optimization**
- **GIN indexes** on all JSONB columns for fast queries
- **Composite indexes** for common query patterns
- **Full-text search** using PostgreSQL's built-in capabilities
- **Partial indexes** for active/archived records

### 5. **Data Integrity**
- **Foreign key constraints** with CASCADE deletes
- **Check constraints** for data validation
- **Triggers** for automatic timestamp updates
- **Row Level Security** for multi-tenant isolation

## Alternatives Considered

### MongoDB
- **Pros**: Natural document storage, flexible schema
- **Cons**: Weaker consistency guarantees, complex joins, limited SQL tooling
- **Verdict**: Rejected due to ACID requirements and complex relationships

### MySQL/MariaDB
- **Pros**: Familiar, good performance, JSON support
- **Cons**: Less mature JSON features, limited full-text search
- **Verdict**: Rejected in favor of PostgreSQL's superior JSON handling

### Pure Relational (no JSONB)
- **Pros**: Strict schema, optimal for known data structures
- **Cons**: Inflexible for evolving requirements, complex migrations
- **Verdict**: Rejected due to need for flexible metadata storage

## Implementation Details

### JSONB Schema Examples
```json
// User preferences
{
  "theme": "light",
  "notifications": {
    "email": true,
    "push": true,
    "board_updates": true
  },
  "dashboard": {
    "layout": "default",
    "widgets": ["boards", "calendar", "journal"]
  }
}

// Card metadata
{
  "tags": ["urgent", "bug"],
  "due_date": "2025-07-15",
  "checklist": [
    {"id": 1, "text": "Fix bug", "completed": false},
    {"id": 2, "text": "Write test", "completed": true}
  ],
  "estimated_hours": 8,
  "actual_hours": 6
}
```

### Index Strategy
```sql
-- JSONB indexes for metadata queries
CREATE INDEX idx_users_preferences ON users USING GIN(preferences);
CREATE INDEX idx_cards_metadata ON cards USING GIN(metadata);

-- Composite indexes for common queries
CREATE INDEX idx_cards_position ON cards(board_id, position);
CREATE INDEX idx_calendar_events_date_range ON calendar_events(start_datetime, end_datetime);

-- Full-text search indexes
CREATE INDEX idx_cards_title_search ON cards USING GIN(to_tsvector('english', title));
```

### Migration Strategy
- **Alembic** for schema migrations
- **Versioned migrations** with rollback support
- **Data migration scripts** for complex transformations
- **Backward compatibility** maintained for 2 versions

## Consequences

### Positive
- **Flexibility**: Easy to add new metadata fields without schema changes
- **Performance**: Optimized for read-heavy workloads with proper indexing
- **Scalability**: Can handle growing data volumes and query complexity
- **Developer Experience**: SQL familiarity with NoSQL flexibility
- **Data Integrity**: Strong consistency guarantees

### Negative
- **Complexity**: Requires PostgreSQL expertise for optimization
- **Storage**: JSONB can be less space-efficient than normalized tables
- **Migrations**: JSONB schema changes require careful planning
- **Tooling**: Some ORM tools have limited JSONB support

### Mitigation Strategies
- **Documentation**: Comprehensive schema documentation and examples
- **Testing**: Extensive testing of JSONB queries and performance
- **Monitoring**: Query performance monitoring and alerting
- **Training**: Team training on PostgreSQL JSONB best practices

## Security Considerations
- **Row Level Security** (RLS) for multi-tenant data isolation
- **Audit logging** for all data modifications
- **Encrypted connections** required for all database access
- **Secrets management** for database credentials
- **Regular backups** with encryption at rest

## Performance Targets
- **Read queries**: < 50ms for 95th percentile
- **Write queries**: < 100ms for 95th percentile
- **Full-text search**: < 200ms for complex queries
- **Concurrent users**: Support for 1000+ concurrent connections

## Monitoring and Maintenance
- **Query performance** monitoring with pg_stat_statements
- **Index usage** tracking and optimization
- **Database size** and growth monitoring
- **Backup and recovery** procedures
- **Regular VACUUM and ANALYZE** operations

## Future Considerations
- **Partitioning** for large tables (calendar_events, ai_commands)
- **Read replicas** for scaling read operations
- **Connection pooling** for improved performance
- **Caching layer** (Redis) for frequently accessed data
- **Archive strategy** for historical data

## Related ADRs
- ADR-002: Authentication and Session Management
- ADR-003: API Design and Rate Limiting
- ADR-004: Real-time Updates with WebSockets

---
**Date**: 2025-07-06  
**Authors**: Development Team  
**Reviewed by**: Technical Lead
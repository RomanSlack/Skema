-- Skema Database Schema
-- Production-ready PostgreSQL schema with JSONB support

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    avatar_url VARCHAR(255),
    preferences JSONB DEFAULT '{
        "theme": "light",
        "notifications": {
            "email": true,
            "push": true,
            "board_updates": true,
            "calendar_reminders": true
        },
        "dashboard": {
            "layout": "default",
            "widgets": ["boards", "calendar", "journal", "recent_activity"]
        }
    }'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- Boards table (Kanban)
CREATE TABLE boards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#6366f1', -- Hex color code
    settings JSONB DEFAULT '{
        "columns": [
            {"id": "todo", "title": "To Do", "color": "#ef4444"},
            {"id": "in_progress", "title": "In Progress", "color": "#f59e0b"},
            {"id": "done", "title": "Done", "color": "#10b981"}
        ],
        "automation": {
            "auto_archive": false,
            "move_completed_cards": false
        },
        "permissions": {
            "public": false,
            "collaborators": []
        }
    }'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE
);

-- Cards table (Kanban items)
CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'todo',
    priority VARCHAR(20) DEFAULT 'medium',
    metadata JSONB DEFAULT '{
        "tags": [],
        "due_date": null,
        "checklist": [],
        "attachments": [],
        "assigned_to": null,
        "estimated_hours": null,
        "actual_hours": null
    }'::jsonb,
    position INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Calendar events table
CREATE TABLE calendar_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    end_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    location VARCHAR(255),
    event_type VARCHAR(50) DEFAULT 'personal',
    color VARCHAR(7) DEFAULT '#3b82f6',
    metadata JSONB DEFAULT '{
        "recurrence": null,
        "attendees": [],
        "reminders": [
            {"type": "notification", "minutes": 15},
            {"type": "email", "minutes": 60}
        ],
        "meeting_link": null,
        "timezone": "UTC"
    }'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_all_day BOOLEAN DEFAULT FALSE,
    is_recurring BOOLEAN DEFAULT FALSE
);

-- Journal entries table
CREATE TABLE journal_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    content TEXT NOT NULL,
    mood VARCHAR(50),
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{
        "weather": null,
        "location": null,
        "custom_fields": {},
        "attachments": [],
        "word_count": 0,
        "reading_time": 0
    }'::jsonb,
    entry_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_private BOOLEAN DEFAULT TRUE,
    is_favorite BOOLEAN DEFAULT FALSE
);

-- AI command history table
CREATE TABLE ai_commands (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    command TEXT NOT NULL,
    response TEXT,
    context_type VARCHAR(50),
    context_id UUID,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    metadata JSONB DEFAULT '{
        "model": "gpt-4",
        "tokens_used": 0,
        "intent": null,
        "confidence": 0.0,
        "source": "command_bar"
    }'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User sessions table (for JWT token management)
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token VARCHAR(255) NOT NULL,
    user_agent TEXT,
    ip_address INET,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Audit log table (for security and compliance)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    old_data JSONB,
    new_data JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance optimization
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);

CREATE INDEX idx_boards_user_id ON boards(user_id);
CREATE INDEX idx_boards_archived ON boards(is_archived);

CREATE INDEX idx_cards_board_id ON cards(board_id);
CREATE INDEX idx_cards_status ON cards(status);
CREATE INDEX idx_cards_priority ON cards(priority);
CREATE INDEX idx_cards_position ON cards(board_id, position);

CREATE INDEX idx_calendar_events_user_id ON calendar_events(user_id);
CREATE INDEX idx_calendar_events_date_range ON calendar_events(start_datetime, end_datetime);
CREATE INDEX idx_calendar_events_type ON calendar_events(event_type);

CREATE INDEX idx_journal_entries_user_id ON journal_entries(user_id);
CREATE INDEX idx_journal_entries_date ON journal_entries(entry_date);
CREATE INDEX idx_journal_entries_tags ON journal_entries USING GIN(tags);

CREATE INDEX idx_ai_commands_user_id ON ai_commands(user_id);
CREATE INDEX idx_ai_commands_context ON ai_commands(context_type, context_id);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(refresh_token);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- JSONB indexes for performance
CREATE INDEX idx_users_preferences ON users USING GIN(preferences);
CREATE INDEX idx_boards_settings ON boards USING GIN(settings);
CREATE INDEX idx_cards_metadata ON cards USING GIN(metadata);
CREATE INDEX idx_calendar_events_metadata ON calendar_events USING GIN(metadata);
CREATE INDEX idx_journal_entries_metadata ON journal_entries USING GIN(metadata);
CREATE INDEX idx_ai_commands_metadata ON ai_commands USING GIN(metadata);

-- Full-text search indexes
CREATE INDEX idx_cards_title_search ON cards USING GIN(to_tsvector('english', title));
CREATE INDEX idx_cards_description_search ON cards USING GIN(to_tsvector('english', description));
CREATE INDEX idx_journal_entries_content_search ON journal_entries USING GIN(to_tsvector('english', content));
CREATE INDEX idx_journal_entries_title_search ON journal_entries USING GIN(to_tsvector('english', title));

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_boards_updated_at BEFORE UPDATE ON boards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cards_updated_at BEFORE UPDATE ON cards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_calendar_events_updated_at BEFORE UPDATE ON calendar_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_journal_entries_updated_at BEFORE UPDATE ON journal_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate journal entry reading time
CREATE OR REPLACE FUNCTION calculate_reading_time(content TEXT)
RETURNS INTEGER AS $$
BEGIN
    -- Average reading speed: 200 words per minute
    RETURN CEIL(array_length(string_to_array(content, ' '), 1) / 200.0);
END;
$$ LANGUAGE 'plpgsql';

-- Function to update journal entry metadata
CREATE OR REPLACE FUNCTION update_journal_entry_stats()
RETURNS TRIGGER AS $$
BEGIN
    NEW.metadata = jsonb_set(
        jsonb_set(
            COALESCE(NEW.metadata, '{}'::jsonb),
            '{word_count}',
            to_jsonb(array_length(string_to_array(NEW.content, ' '), 1))
        ),
        '{reading_time}',
        to_jsonb(calculate_reading_time(NEW.content))
    );
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER update_journal_entry_stats_trigger
    BEFORE INSERT OR UPDATE ON journal_entries
    FOR EACH ROW EXECUTE FUNCTION update_journal_entry_stats();

-- Row Level Security (RLS) policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE boards ENABLE ROW LEVEL SECURITY;
ALTER TABLE cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- RLS policies for user data isolation
CREATE POLICY users_own_data ON users
    FOR ALL
    TO authenticated
    USING (auth.uid() = id);

CREATE POLICY boards_own_data ON boards
    FOR ALL
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY cards_own_data ON cards
    FOR ALL
    TO authenticated
    USING (auth.uid() = (SELECT user_id FROM boards WHERE id = board_id));

CREATE POLICY calendar_events_own_data ON calendar_events
    FOR ALL
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY journal_entries_own_data ON journal_entries
    FOR ALL
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY ai_commands_own_data ON ai_commands
    FOR ALL
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY user_sessions_own_data ON user_sessions
    FOR ALL
    TO authenticated
    USING (auth.uid() = user_id);

-- Initial data setup
INSERT INTO users (email, hashed_password, full_name, email_verified) VALUES
('demo@skema.app', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewRuMzfXtKWfKGWG', 'Demo User', true)
ON CONFLICT (email) DO NOTHING;

-- Get the demo user ID for inserting sample data
DO $$
DECLARE
    demo_user_id UUID;
BEGIN
    SELECT id INTO demo_user_id FROM users WHERE email = 'demo@skema.app';
    
    IF demo_user_id IS NOT NULL THEN
        -- Insert sample board
        INSERT INTO boards (user_id, title, description) VALUES
        (demo_user_id, 'My First Board', 'Welcome to your Kanban board!')
        ON CONFLICT DO NOTHING;
        
        -- Insert sample calendar event
        INSERT INTO calendar_events (user_id, title, description, start_datetime, end_datetime) VALUES
        (demo_user_id, 'Welcome to Skema', 'Get familiar with the calendar feature', 
         CURRENT_TIMESTAMP + INTERVAL '1 hour', CURRENT_TIMESTAMP + INTERVAL '2 hours')
        ON CONFLICT DO NOTHING;
        
        -- Insert sample journal entry
        INSERT INTO journal_entries (user_id, title, content, entry_date) VALUES
        (demo_user_id, 'My First Entry', 'Welcome to your journal! This is where you can write down your thoughts, ideas, and reflections.', CURRENT_DATE)
        ON CONFLICT DO NOTHING;
    END IF;
END $$;
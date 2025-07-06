"""Initial database schema for Skema productivity app

Revision ID: 001
Revises: 
Create Date: 2025-07-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(255), nullable=True),
        sa.Column('preferences', postgresql.JSONB(), nullable=True, 
                  server_default=sa.text("""'{
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
                  }'::jsonb""")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    
    # Create boards table
    op.create_table('boards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(7), nullable=False, server_default='#6366f1'),
        sa.Column('settings', postgresql.JSONB(), nullable=True, 
                  server_default=sa.text("""'{
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
                  }'::jsonb""")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create cards table
    op.create_table('cards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('board_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='todo'),
        sa.Column('priority', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, 
                  server_default=sa.text("""'{
                      "tags": [],
                      "due_date": null,
                      "checklist": [],
                      "attachments": [],
                      "assigned_to": null,
                      "estimated_hours": null,
                      "actual_hours": null
                  }'::jsonb""")),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['board_id'], ['boards.id'], ondelete='CASCADE'),
    )
    
    # Create calendar_events table
    op.create_table('calendar_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_datetime', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('end_datetime', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False, server_default='personal'),
        sa.Column('color', sa.String(7), nullable=False, server_default='#3b82f6'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, 
                  server_default=sa.text("""'{
                      "recurrence": null,
                      "attendees": [],
                      "reminders": [
                          {"type": "notification", "minutes": 15},
                          {"type": "email", "minutes": 60}
                      ],
                      "meeting_link": null,
                      "timezone": "UTC"
                  }'::jsonb""")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_all_day', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_recurring', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create journal_entries table
    op.create_table('journal_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('mood', sa.String(50), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True, server_default='{}'),
        sa.Column('meta_data', postgresql.JSONB(), nullable=True, 
                  server_default=sa.text("""'{
                      "weather": null,
                      "location": null,
                      "custom_fields": {},
                      "attachments": [],
                      "word_count": 0,
                      "reading_time": 0
                  }'::jsonb""")),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_private', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create ai_commands table
    op.create_table('ai_commands',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('command', sa.Text(), nullable=False),
        sa.Column('response', sa.Text(), nullable=True),
        sa.Column('context_type', sa.String(50), nullable=True),
        sa.Column('context_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, 
                  server_default=sa.text("""'{
                      "model": "gpt-4",
                      "tokens_used": 0,
                      "intent": null,
                      "confidence": 0.0,
                      "source": "command_bar"
                  }'::jsonb""")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create user_sessions table
    op.create_table('user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('refresh_token', sa.String(255), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('old_data', postgresql.JSONB(), nullable=True),
        sa.Column('new_data', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    
    # Create indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_active', 'users', ['is_active'])
    
    op.create_index('idx_boards_user_id', 'boards', ['user_id'])
    op.create_index('idx_boards_archived', 'boards', ['is_archived'])
    
    op.create_index('idx_cards_board_id', 'cards', ['board_id'])
    op.create_index('idx_cards_status', 'cards', ['status'])
    op.create_index('idx_cards_priority', 'cards', ['priority'])
    op.create_index('idx_cards_position', 'cards', ['board_id', 'position'])
    
    op.create_index('idx_calendar_events_user_id', 'calendar_events', ['user_id'])
    op.create_index('idx_calendar_events_date_range', 'calendar_events', ['start_datetime', 'end_datetime'])
    op.create_index('idx_calendar_events_type', 'calendar_events', ['event_type'])
    
    op.create_index('idx_journal_entries_user_id', 'journal_entries', ['user_id'])
    op.create_index('idx_journal_entries_date', 'journal_entries', ['entry_date'])
    
    op.create_index('idx_ai_commands_user_id', 'ai_commands', ['user_id'])
    op.create_index('idx_ai_commands_context', 'ai_commands', ['context_type', 'context_id'])
    
    op.create_index('idx_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('idx_user_sessions_token', 'user_sessions', ['refresh_token'])
    op.create_index('idx_user_sessions_expires', 'user_sessions', ['expires_at'])
    
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])
    
    # Create GIN indexes for JSONB and array columns
    op.create_index('idx_users_preferences', 'users', ['preferences'], postgresql_using='gin')
    op.create_index('idx_boards_settings', 'boards', ['settings'], postgresql_using='gin')
    op.create_index('idx_cards_metadata', 'cards', ['metadata'], postgresql_using='gin')
    op.create_index('idx_calendar_events_metadata', 'calendar_events', ['metadata'], postgresql_using='gin')
    op.create_index('idx_journal_entries_metadata', 'journal_entries', ['meta_data'], postgresql_using='gin')
    op.create_index('idx_ai_commands_metadata', 'ai_commands', ['metadata'], postgresql_using='gin')
    op.create_index('idx_journal_entries_tags', 'journal_entries', ['tags'], postgresql_using='gin')
    
    # Create full-text search indexes
    op.execute("""
        CREATE INDEX idx_cards_title_search ON cards USING GIN(to_tsvector('english', title));
        CREATE INDEX idx_cards_description_search ON cards USING GIN(to_tsvector('english', description));
        CREATE INDEX idx_journal_entries_content_search ON journal_entries USING GIN(to_tsvector('english', content));
        CREATE INDEX idx_journal_entries_title_search ON journal_entries USING GIN(to_tsvector('english', title));
    """)
    
    # Create update timestamp trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create triggers for updated_at columns
    op.execute("""
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
    """)
    
    # Create journal entry stats function and trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION calculate_reading_time(content TEXT)
        RETURNS INTEGER AS $$
        BEGIN
            RETURN CEIL(array_length(string_to_array(content, ' '), 1) / 200.0);
        END;
        $$ LANGUAGE 'plpgsql';
        
        CREATE OR REPLACE FUNCTION update_journal_entry_stats()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.meta_data = jsonb_set(
                jsonb_set(
                    COALESCE(NEW.meta_data, '{}'::jsonb),
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
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("""
        DROP TRIGGER IF EXISTS update_journal_entry_stats_trigger ON journal_entries;
        DROP TRIGGER IF EXISTS update_journal_entries_updated_at ON journal_entries;
        DROP TRIGGER IF EXISTS update_calendar_events_updated_at ON calendar_events;
        DROP TRIGGER IF EXISTS update_cards_updated_at ON cards;
        DROP TRIGGER IF EXISTS update_boards_updated_at ON boards;
        DROP TRIGGER IF EXISTS update_users_updated_at ON users;
    """)
    
    # Drop functions
    op.execute("""
        DROP FUNCTION IF EXISTS update_journal_entry_stats();
        DROP FUNCTION IF EXISTS calculate_reading_time(TEXT);
        DROP FUNCTION IF EXISTS update_updated_at_column();
    """)
    
    # Drop tables in reverse order
    op.drop_table('audit_logs')
    op.drop_table('user_sessions')
    op.drop_table('ai_commands')
    op.drop_table('journal_entries')
    op.drop_table('calendar_events')
    op.drop_table('cards')
    op.drop_table('boards')
    op.drop_table('users')
    
    # Drop extension
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
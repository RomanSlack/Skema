-- Skema Database Seed Data
-- Sample data for development and testing

-- Insert demo user (password: demo123)
INSERT INTO users (email, hashed_password, full_name, email_verified) VALUES
('demo@skema.app', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewRuMzfXtKWfKGWG', 'Demo User', true)
ON CONFLICT (email) DO NOTHING;

-- Get the demo user ID for inserting sample data
DO $$
DECLARE
    demo_user_id UUID;
    sample_board_id UUID;
    personal_board_id UUID;
    work_board_id UUID;
BEGIN
    SELECT id INTO demo_user_id FROM users WHERE email = 'demo@skema.app';
    
    IF demo_user_id IS NOT NULL THEN
        -- Insert sample boards
        INSERT INTO boards (user_id, title, description, color) VALUES
        (demo_user_id, 'Personal Projects', 'Track your personal goals and projects', '#6366f1'),
        (demo_user_id, 'Work Tasks', 'Manage your work-related tasks and deadlines', '#059669'),
        (demo_user_id, 'Learning Goals', 'Track your learning objectives and progress', '#dc2626')
        ON CONFLICT DO NOTHING;
        
        -- Get board IDs for adding cards
        SELECT id INTO sample_board_id FROM boards WHERE user_id = demo_user_id AND title = 'Personal Projects';
        SELECT id INTO personal_board_id FROM boards WHERE user_id = demo_user_id AND title = 'Work Tasks';
        SELECT id INTO work_board_id FROM boards WHERE user_id = demo_user_id AND title = 'Learning Goals';
        
        -- Insert sample cards for Personal Projects board
        INSERT INTO cards (board_id, title, description, status, priority, position, metadata) VALUES
        (sample_board_id, 'Set up home office', 'Create a comfortable and productive workspace', 'todo', 'high', 1, 
         '{"tags": ["home", "productivity"], "due_date": "2025-07-15", "estimated_hours": 8}'),
        (sample_board_id, 'Plan vacation', 'Research and book summer vacation destinations', 'todo', 'medium', 2,
         '{"tags": ["travel", "personal"], "due_date": "2025-07-20", "estimated_hours": 4}'),
        (sample_board_id, 'Learn new cooking recipe', 'Try making homemade pasta from scratch', 'in_progress', 'low', 3,
         '{"tags": ["cooking", "skills"], "estimated_hours": 2}'),
        (sample_board_id, 'Organize photo collection', 'Sort and backup digital photos from last year', 'done', 'low', 4,
         '{"tags": ["organization", "memories"], "estimated_hours": 6, "actual_hours": 5}');
        
        -- Insert sample cards for Work Tasks board
        INSERT INTO cards (board_id, title, description, status, priority, position, metadata) VALUES
        (personal_board_id, 'Complete project proposal', 'Draft and submit Q3 project proposal', 'todo', 'high', 1,
         '{"tags": ["project", "deadline"], "due_date": "2025-07-10", "estimated_hours": 12}'),
        (personal_board_id, 'Team meeting preparation', 'Prepare slides and agenda for weekly team meeting', 'todo', 'medium', 2,
         '{"tags": ["meeting", "team"], "due_date": "2025-07-08", "estimated_hours": 2}'),
        (personal_board_id, 'Code review', 'Review pull requests from team members', 'in_progress', 'medium', 3,
         '{"tags": ["code", "review"], "estimated_hours": 3}'),
        (personal_board_id, 'Update documentation', 'Update API documentation with recent changes', 'done', 'low', 4,
         '{"tags": ["documentation", "api"], "estimated_hours": 4, "actual_hours": 3}');
        
        -- Insert sample cards for Learning Goals board
        INSERT INTO cards (board_id, title, description, status, priority, position, metadata) VALUES
        (work_board_id, 'Complete React course', 'Finish advanced React patterns course on Udemy', 'todo', 'high', 1,
         '{"tags": ["learning", "react"], "due_date": "2025-08-01", "estimated_hours": 20}'),
        (work_board_id, 'Practice TypeScript', 'Build a small project using TypeScript', 'in_progress', 'medium', 2,
         '{"tags": ["typescript", "practice"], "estimated_hours": 15}'),
        (work_board_id, 'Read design patterns book', 'Read "Design Patterns" by Gang of Four', 'done', 'medium', 3,
         '{"tags": ["books", "architecture"], "estimated_hours": 25, "actual_hours": 28}');
        
        -- Insert sample calendar events
        INSERT INTO calendar_events (user_id, title, description, start_datetime, end_datetime, event_type, color, metadata) VALUES
        (demo_user_id, 'Team Standup', 'Daily team standup meeting', 
         CURRENT_TIMESTAMP + INTERVAL '1 day' + INTERVAL '9 hours', 
         CURRENT_TIMESTAMP + INTERVAL '1 day' + INTERVAL '9 hours 30 minutes', 
         'work', '#059669',
         '{"recurrence": {"type": "daily", "days": ["mon", "tue", "wed", "thu", "fri"]}, "meeting_link": "https://meet.google.com/abc-def-ghi"}'),
        
        (demo_user_id, 'Doctor Appointment', 'Annual checkup with Dr. Smith', 
         CURRENT_TIMESTAMP + INTERVAL '3 days' + INTERVAL '14 hours', 
         CURRENT_TIMESTAMP + INTERVAL '3 days' + INTERVAL '15 hours', 
         'personal', '#dc2626',
         '{"reminders": [{"type": "notification", "minutes": 60}, {"type": "email", "minutes": 1440}], "location": "123 Health St, City"}'),
        
        (demo_user_id, 'Project Deadline', 'Q3 project proposal due', 
         CURRENT_TIMESTAMP + INTERVAL '4 days' + INTERVAL '17 hours', 
         CURRENT_TIMESTAMP + INTERVAL '4 days' + INTERVAL '17 hours', 
         'work', '#f59e0b',
         '{"reminders": [{"type": "notification", "minutes": 120}, {"type": "email", "minutes": 2880}]}'),
        
        (demo_user_id, 'Vacation Planning', 'Research and book summer vacation', 
         CURRENT_TIMESTAMP + INTERVAL '7 days' + INTERVAL '19 hours', 
         CURRENT_TIMESTAMP + INTERVAL '7 days' + INTERVAL '21 hours', 
         'personal', '#6366f1',
         '{"reminders": [{"type": "notification", "minutes": 30}]}'),
        
        (demo_user_id, 'Code Review Session', 'Review team pull requests', 
         CURRENT_TIMESTAMP + INTERVAL '2 days' + INTERVAL '15 hours', 
         CURRENT_TIMESTAMP + INTERVAL '2 days' + INTERVAL '17 hours', 
         'work', '#059669',
         '{"meeting_link": "https://github.com/team/repo/pulls"}');
        
        -- Insert sample journal entries
        INSERT INTO journal_entries (user_id, title, content, entry_date, mood, tags, metadata) VALUES
        (demo_user_id, 'Starting My Productivity Journey', 
         'Today I decided to get more organized with my tasks and goals. I''ve been feeling scattered lately and I think having a system like this will help me stay focused. I''m excited to see how this impacts my daily routine and overall productivity.',
         CURRENT_DATE - INTERVAL '2 days', 'excited', 
         ARRAY['productivity', 'goals', 'organization'],
         '{"weather": "sunny", "location": "home office"}'),
        
        (demo_user_id, 'Reflection on Work-Life Balance', 
         'Had a long day at work today, but I managed to finish the documentation update. I''m realizing how important it is to set boundaries between work and personal time. Need to be more intentional about logging off and spending quality time with family.',
         CURRENT_DATE - INTERVAL '1 day', 'thoughtful', 
         ARRAY['work', 'balance', 'family'],
         '{"weather": "cloudy", "location": "home"}'),
        
        (demo_user_id, 'Weekend Plans and Goals', 
         'Looking forward to the weekend! Planning to work on my home office setup and maybe try that new pasta recipe I''ve been wanting to attempt. Also need to do some photo organization - my digital photos are a mess. Small steps towards a more organized life.',
         CURRENT_DATE, 'optimistic', 
         ARRAY['weekend', 'projects', 'cooking'],
         '{"weather": "partly cloudy", "location": "living room"}');
        
        -- Insert sample AI command history
        INSERT INTO ai_commands (user_id, command, response, context_type, execution_time_ms, success, metadata) VALUES
        (demo_user_id, 'Create a new card for project planning', 
         'I''ve created a new card titled "Project Planning" in your Personal Projects board.',
         'board', 245, true,
         '{"model": "gpt-4", "tokens_used": 35, "intent": "create_card", "confidence": 0.95}'),
        
        (demo_user_id, 'Schedule a meeting for next Tuesday at 2 PM', 
         'I''ve scheduled a meeting for next Tuesday at 2:00 PM. What would you like to call this meeting?',
         'calendar', 189, true,
         '{"model": "gpt-4", "tokens_used": 42, "intent": "schedule_event", "confidence": 0.88}'),
        
        (demo_user_id, 'Add a journal entry about my day', 
         'I''ve created a new journal entry for today. You can add your thoughts and reflections.',
         'journal', 156, true,
         '{"model": "gpt-4", "tokens_used": 28, "intent": "create_journal_entry", "confidence": 0.92}');
        
        -- Update user preferences with more detailed settings
        UPDATE users SET preferences = '{
            "theme": "light",
            "notifications": {
                "email": true,
                "push": true,
                "board_updates": true,
                "calendar_reminders": true,
                "daily_digest": true
            },
            "dashboard": {
                "layout": "default",
                "widgets": ["boards", "calendar", "journal", "recent_activity", "ai_suggestions"]
            },
            "ai": {
                "auto_suggestions": true,
                "command_history": true,
                "context_awareness": true
            },
            "privacy": {
                "analytics": true,
                "crash_reports": true,
                "usage_data": false
            }
        }'::jsonb
        WHERE id = demo_user_id;
        
        RAISE NOTICE 'Sample data inserted successfully for demo user: %', demo_user_id;
    ELSE
        RAISE NOTICE 'Demo user not found. Please run the schema.sql file first.';
    END IF;
END $$;
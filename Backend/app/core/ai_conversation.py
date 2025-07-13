"""
AI Conversation Handler with OpenAI Integration
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import openai

from app.config import settings
from app.models.user import User
from app.core.ai_tools import get_tools_for_openai, execute_ai_tool, AI_TOOLS_REGISTRY

logger = logging.getLogger(__name__)


class AIConversationHandler:
    """Handler for AI conversations with tool calling support"""
    
    def __init__(self):
        self.client = None
        if settings.openai_api_key:
            openai.api_key = settings.openai_api_key
            self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
    def _get_system_prompt(self, user: User) -> str:
        """Get the system prompt for the AI assistant"""
        now = datetime.now(timezone.utc)
        return f"""You are Skema AI, a helpful assistant integrated into a productivity application. 
        
You help users manage their tasks, schedule events, write journal entries, and organize their work using natural language commands.

Current user: {user.full_name or user.email}

=== CURRENT DATE & TIME ===
Date: {now.strftime("%A, %B %d, %Y")}
Time: {now.strftime("%I:%M %p UTC")}
ISO Format: {now.strftime("%Y-%m-%dT%H:%M:%SZ")}

Use this for relative dates:
- "today" = {now.strftime("%Y-%m-%d")}
- "tomorrow" = {(now + timedelta(days=1)).strftime("%Y-%m-%d")}
- "next week" = {(now + timedelta(days=7)).strftime("%Y-%m-%d")}
- "this evening" = {now.strftime("%Y-%m-%d")}T18:00:00Z
- "this afternoon" = {now.strftime("%Y-%m-%d")}T14:00:00Z
- "this morning" = {now.strftime("%Y-%m-%d")}T09:00:00Z

You have access to these tools - USE THEM when users request actions:

1. **create_calendar_event** - For scheduling meetings, appointments, events
   - Required: title, start_datetime (ISO format: 2025-07-10T14:00:00Z)
   - Optional: description, end_datetime, location, is_all_day
   - Examples: "meeting at 2pm July 10th", "dentist appointment tomorrow"

2. **create_journal_entry** - For recording thoughts, feelings, experiences
   - Required: title, content
   - Optional: mood (great/good/okay/bad/terrible), entry_date
   - Examples: "I felt great after the gym", "today's reflection"

3. **create_board** - For organizing projects with Kanban boards
   - Required: title
   - Optional: description
   - Examples: "startup ideas board", "home renovation project"

4. **create_card** - For adding tasks to existing boards
   - Required: board_id, title
   - Optional: description, due_date
   - Use get_boards first to find the right board_id

5. **get_boards** - List user's existing boards to get board IDs

6. **create_quest** - For creating daily tasks (rolling to-do system)
   - Required: content
   - Optional: date_created, date_due, time_due
   - Examples: "buy groceries", "finish report by 5pm", "call mom tomorrow"

7. **complete_quest** - For marking quest tasks as complete/incomplete
   - Required: quest_content (partial match)
   - Optional: quest_date, is_complete
   - Examples: "mark groceries as done", "complete the report task"

8. **get_quests** - Get quest tasks for a specific date
   - Optional: quest_date, include_completed
   - Examples: "show my tasks for today", "what's on my quest list"

IMPORTANT INSTRUCTIONS:
- ALWAYS use tools when users request creating/scheduling/managing something
- For daily tasks/todos, use Quest tools instead of cards/boards
- ALWAYS convert dates/times to ISO format using current date context above

DATE & TIME CONVERSION RULES:
- "July 10th 2025 at 2 PM" → "2025-07-10T14:00:00Z"
- "tomorrow at 3pm" → "{(now + timedelta(days=1)).strftime("%Y-%m-%d")}T15:00:00Z"
- "today at noon" → "{now.strftime("%Y-%m-%d")}T12:00:00Z"
- "next Monday at 9am" → [calculate next Monday]T09:00:00Z
- Time formats: "2 PM"/"2pm"/"2:00 PM" = "14:00", "9 AM"/"9am" = "09:00"

WHEN CREATING EVENTS:
- Extract title from context (meeting with X, appointment, etc.)
- Default duration: 1 hour if not specified
- Confirm with human-readable format after creation

Examples:
User: "I have a meeting at 2:00 p.m. July 10th 2025 name the title Meeting With Dan"
→ create_calendar_event(title="Meeting With Dan", start_datetime="2025-07-10T14:00:00Z")
→ Response: "Perfect! I've scheduled 'Meeting With Dan' for Thursday, July 10th, 2025 at 2:00 PM."
"""
    
    async def process_message(
        self,
        message: str,
        user: User,
        session,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Process a user message and return AI response with potential tool calls"""
        
        if not self.client:
            return {
                "success": False,
                "response": "AI functionality is not available. Please configure OpenAI API key.",
                "error": "OpenAI API key not configured"
            }
        
        try:
            # Build conversation messages
            messages = [
                {"role": "system", "content": self._get_system_prompt(user)}
            ]
            
            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history[-10:])  # Keep last 10 messages for context
            
            # Add current user message
            messages.append({"role": "user", "content": message})
            
            # Get available tools
            tools = get_tools_for_openai()
            
            # Make OpenAI API call
            response = self.client.chat.completions.create(
                model=settings.ai_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=settings.ai_max_tokens,
                temperature=0.7
            )
            
            assistant_message = response.choices[0].message
            
            # Handle tool calls
            tool_results = []
            if assistant_message.tool_calls:
                # Add the assistant message with tool calls first
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [{
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    } for tool_call in assistant_message.tool_calls]
                })
                
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # Execute the tool
                    result = await execute_ai_tool(tool_name, tool_args, user, session)
                    tool_results.append({
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "result": result
                    })
                    
                    # Add tool result to conversation for context
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })
                
                # Get final response after tool execution
                final_response = self.client.chat.completions.create(
                    model=settings.ai_model,
                    messages=messages,
                    max_tokens=settings.ai_max_tokens,
                    temperature=0.7
                )
                
                response_text = final_response.choices[0].message.content
            else:
                response_text = assistant_message.content
            
            # Calculate token usage
            total_tokens = response.usage.total_tokens if hasattr(response, 'usage') else 0
            
            return {
                "success": True,
                "response": response_text,
                "tool_calls": tool_results,
                "metadata": {
                    "model": settings.ai_model,
                    "tokens_used": total_tokens,
                    "tools_used": len(tool_results),
                    "message_count": len(messages)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in AI conversation: {e}")
            return {
                "success": False,
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "error": str(e)
            }
    
    async def get_quick_suggestions(self, user: User) -> List[str]:
        """Get quick suggestion prompts for the user"""
        return [
            "Add a journal entry about how I'm feeling today",
            "Schedule a meeting for tomorrow at 2 PM",
            "Create a board for my new project",
            "Show me all my boards",
            "Add a card to track my progress",
            "Plan a break in my calendar",
            "Write about today's achievements",
            "Create a reminder for next week"
        ]
    
    def parse_natural_date(self, date_str: str) -> Optional[datetime]:
        """Parse natural language dates (basic implementation)"""
        # This is a simplified implementation
        # In production, you might want to use a library like dateparser
        now = datetime.now(timezone.utc)
        
        date_str = date_str.lower().strip()
        
        if "today" in date_str:
            return now
        elif "tomorrow" in date_str:
            return now.replace(day=now.day + 1)
        elif "next week" in date_str:
            return now.replace(day=now.day + 7)
        
        # Try to parse ISO format
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None


# Global conversation handler instance
ai_conversation_handler = AIConversationHandler()
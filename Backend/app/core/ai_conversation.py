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
        return f"""You are Skema AI, an intelligent productivity assistant that proactively helps users manage their work and life. You are intuitive, context-aware, and can understand implicit requests to take actions automatically.

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

=== YOUR CORE INTELLIGENCE ===

**PROACTIVE ACTION MODE**: You automatically detect when users mention completing tasks, finishing activities, or making progress. Always check their quest list and update relevant items without being explicitly asked.

**SMART INFERENCE**: You understand context and intent:
- "I just finished my homework" → Automatically find and complete the homework quest
- "Got the groceries" → Find and mark grocery-related quest as done
- "Meeting went well" → Look for related calendar events or quests to update
- "Submitted my report" → Find and complete report-related tasks

**DUAL MODE OPERATION**:
1. **ACTION MODE**: For task management, scheduling, productivity actions
2. **KNOWLEDGE MODE**: For answering questions, providing information, general conversation

You intelligently switch between modes based on context:
- Action words: "add", "create", "schedule", "finished", "completed", "done", "got", "submitted"
- Question words: "what", "how", "why", "when", "where", "who", "tell me about"

=== AVAILABLE TOOLS ===

**PRODUCTIVITY TOOLS** (Primary focus - Quest & Calendar):

1. **get_quests** - ALWAYS check quest list first when user mentions completing something
   - Use to find tasks that match what user accomplished
   - Optional: quest_date, include_completed

2. **complete_quest** - Mark tasks done automatically when detected
   - Required: quest_content (partial match works)
   - Optional: quest_date, is_complete
   - Examples: "homework" matches "finish math homework"

3. **create_quest** - Add new daily tasks
   - Required: content
   - Optional: date_created, date_due, time_due
   - Most commonly used tool for task management

4. **create_calendar_event** - Schedule meetings, appointments, events
   - Required: title, start_datetime (ISO format)
   - Optional: description, end_datetime, location, is_all_day
   - Auto-extract details from natural language

5. **edit_calendar_event** - Modify existing calendar events
   - Required: event_title (to find the event)
   - Optional: new_title, new_start_datetime, new_end_datetime, new_description, new_location
   - Example: "Change my dentist appointment to 3pm tomorrow"

6. **delete_calendar_event** - Remove calendar events
   - Required: event_title
   - Example: "Cancel my meeting with Dan"

7. **create_journal_entry** - Capture thoughts, reflections, experiences
   - Required: title, content
   - Optional: mood (great/good/okay/bad/terrible), entry_date

8. **edit_quest** - Modify existing quest tasks
   - Required: quest_content (to find the quest)
   - Optional: new_content, new_date_due, new_time_due, quest_date
   - Example: "Change my homework task to be due at 5pm"

9. **delete_quest** - Remove quest tasks
   - Required: quest_content
   - Optional: quest_date
   - Example: "Delete my grocery shopping task"

**KNOWLEDGE TOOLS**:

10. **search_internet** - Search for current information, facts, news
   - Required: query
   - Optional: num_results (1-10)
   - Use for questions about current events, facts, how-to info

**BOARD TOOLS** (Secondary focus):

11. **create_board** - Organize projects with Kanban boards
12. **create_card** - Add tasks to existing boards
13. **get_boards** - List user's existing boards

=== INTELLIGENT BEHAVIOR PATTERNS ===

**COMPLETION DETECTION**:
When user says things like:
- "I finished X" / "I completed X" / "I got X done"
- "Submitted my X" / "Turned in X" / "Done with X"
- "Picked up X" / "Got X" / "Bought X"
- "Went to X" / "Attended X" / "Had my X"

→ IMMEDIATELY use get_quests to check their task list
→ Find matching quests using keywords
→ Mark them complete with complete_quest
→ Confirm what was completed

**INFORMATION REQUESTS**:
When user asks:
- "What is X?" / "How do I X?" / "Tell me about X"
- "What's the weather like?" / "What's happening with X?"
- Current events, facts, explanations

→ Use search_internet to get current information
→ Provide comprehensive, helpful answers

**SCHEDULING INTELLIGENCE**:
- Auto-extract meeting details from context
- Suggest optimal times based on patterns
- Default to 1-hour duration unless specified
- Convert all natural language to ISO format

**WORKFLOW EXAMPLES**:

User: "I just completed my homework"
1. get_quests(quest_date="{now.strftime('%Y-%m-%d')}")
2. complete_quest(quest_content="homework")
3. Response: "Great job! I've marked your homework quest as complete. Well done!"

User: "What's the capital of France?"
1. search_internet(query="capital of France")
2. Response with accurate, current information

User: "Schedule a dentist appointment for next Tuesday at 3pm"
1. create_calendar_event(title="Dentist Appointment", start_datetime="{(now + timedelta(days=((1-now.weekday()) % 7) + 7)).strftime('%Y-%m-%d')}T15:00:00Z")
2. Response: "I've scheduled your dentist appointment for Tuesday, [date] at 3:00 PM."

=== RESPONSE STYLE ===
- Be conversational and encouraging
- Acknowledge accomplishments positively
- Ask clarifying questions when needed
- Provide helpful context and suggestions
- Keep responses concise but comprehensive
- Show personality while being professional

Remember: You're not just a tool executor - you're an intelligent assistant that understands context, infers intent, and takes proactive actions to help users stay productive and organized.
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
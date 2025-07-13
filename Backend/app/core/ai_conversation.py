"""
AI Conversation Handler with OpenAI Integration
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import openai
import asyncio
from collections import defaultdict

from app.config import settings
from app.models.user import User
from app.core.ai_tools import get_tools_for_openai, execute_ai_tool, AI_TOOLS_REGISTRY

logger = logging.getLogger(__name__)


class ConversationMemory:
    """In-memory conversation history management with automatic cleanup"""
    
    def __init__(self, max_messages_per_user: int = 15, cleanup_interval_minutes: int = 30):
        self.conversations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.last_activity: Dict[str, datetime] = {}
        self.max_messages_per_user = max_messages_per_user  # 3 exchanges with tools = ~15 messages (user+assistant+tools)
        self.cleanup_interval_minutes = cleanup_interval_minutes
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """Periodically clean up old conversations"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_minutes * 60)
                await self.cleanup_old_conversations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in conversation cleanup: {e}")
    
    async def cleanup_old_conversations(self, max_age_hours: int = 2):
        """Remove conversations older than max_age_hours"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        users_to_remove = []
        
        for user_id, last_activity in self.last_activity.items():
            if last_activity < cutoff_time:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            if user_id in self.conversations:
                del self.conversations[user_id]
            del self.last_activity[user_id]
        
        if users_to_remove:
            logger.info(f"Cleaned up {len(users_to_remove)} old conversation sessions")
    
    def add_message(self, user_id: str, role: str, content: str, tool_calls: Optional[List[Dict]] = None):
        """Add a message to user's conversation history"""
        message = {"role": role, "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        
        self.conversations[user_id].append(message)
        self.last_activity[user_id] = datetime.now(timezone.utc)
        
        # Keep only the most recent messages, but ensure we don't break tool_call pairs
        self._trim_conversation(user_id)
    
    def add_tool_result(self, user_id: str, tool_call_id: str, result: Dict[str, Any]):
        """Add a tool result message to user's conversation history"""
        message = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": json.dumps(result)
        }
        
        self.conversations[user_id].append(message)
        self.last_activity[user_id] = datetime.now(timezone.utc)
        
        # Keep only the most recent messages, but ensure we don't break tool_call pairs
        self._trim_conversation(user_id)
    
    def _trim_conversation(self, user_id: str):
        """Trim conversation while preserving tool_call/tool message pairs"""
        messages = self.conversations[user_id]
        
        # If we're over the limit, trim from the beginning
        while len(messages) > self.max_messages_per_user:
            # Find the first complete conversation unit to remove
            # A unit could be: user -> assistant -> tool(s), or just user -> assistant
            if len(messages) >= 2:
                # Remove the first message
                first_msg = messages.pop(0)
                
                # If it was an assistant message with tool_calls, also remove corresponding tool messages
                if first_msg.get("role") == "assistant" and first_msg.get("tool_calls"):
                    tool_call_ids = {tc["id"] for tc in first_msg["tool_calls"]}
                    
                    # Remove corresponding tool messages
                    while (messages and 
                           messages[0].get("role") == "tool" and 
                           messages[0].get("tool_call_id") in tool_call_ids):
                        messages.pop(0)
            else:
                break
    
    def get_conversation_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a user"""
        self.last_activity[user_id] = datetime.now(timezone.utc)
        return self.conversations[user_id].copy()
    
    def clear_conversation(self, user_id: str):
        """Clear conversation history for a user"""
        if user_id in self.conversations:
            del self.conversations[user_id]
        if user_id in self.last_activity:
            del self.last_activity[user_id]


class AIConversationHandler:
    """Handler for AI conversations with tool calling support and session memory"""
    
    def __init__(self):
        self.client = None
        self.memory = ConversationMemory()
        if settings.openai_api_key:
            openai.api_key = settings.openai_api_key
            self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
    def _get_system_prompt(self, user: User) -> str:
        """Get the system prompt for the AI assistant"""
        now = datetime.now(timezone.utc)
        return f"""You are Skema AI, an intelligent productivity assistant that proactively helps users manage their work and life. You are intuitive, context-aware, and can understand implicit requests to take actions automatically.

Current user: {user.full_name or user.email}

=== CURRENT DATE & TIME ===
**User Timezone**: Eastern Time (America/New_York)
Date: {now.strftime("%A, %B %d, %Y")}
Time: {now.strftime("%I:%M %p UTC")}
ISO Format: {now.strftime("%Y-%m-%dT%H:%M:%SZ")}

**CRITICAL**: All times mentioned by user are in Eastern Time by default. Convert them to UTC for storage.

Use this for relative dates:
- "today" = {now.strftime("%Y-%m-%d")}
- "tomorrow" = {(now + timedelta(days=1)).strftime("%Y-%m-%d")}
- "next week" = {(now + timedelta(days=7)).strftime("%Y-%m-%d")}
- "this evening" = {now.strftime("%Y-%m-%d")}T23:00:00Z (6pm Eastern)
- "this afternoon" = {now.strftime("%Y-%m-%d")}T19:00:00Z (2pm Eastern)
- "this morning" = {now.strftime("%Y-%m-%d")}T14:00:00Z (9am Eastern)

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
   - Required: title, start_datetime (ISO format in UTC)
   - Optional: description, end_datetime, location, is_all_day
   - **TIMEZONE CONVERSION**: User times are Eastern → Add 4-5 hours to convert to UTC
   - Examples: "2 PM" Eastern = "18:00" UTC → "2025-07-14T18:00:00Z"

5. **edit_calendar_event** - Modify existing calendar events
   - Required: event_title (to find the event)
   - Optional: new_title, new_start_datetime, new_end_datetime, new_description, new_location
   - **TIMEZONE CONVERSION**: Convert Eastern times to UTC (add 4-5 hours)
   - Example: "Change my dentist appointment to 3pm tomorrow" → "19:00" UTC

6. **delete_calendar_event** - Remove calendar events
   - Required: event_title
   - Example: "Cancel my meeting with Dan"

7. **get_calendar_events** - Retrieve calendar events for specific dates
   - Optional: start_date, end_date (YYYY-MM-DD format), limit
   - Defaults to today if no dates specified
   - **ALWAYS use this tool when users ask about their calendar or schedule**
   - Examples: "What's on my calendar today?", "Show me this week's meetings"

8. **create_journal_entry** - Capture thoughts, reflections, experiences
   - Required: title, content
   - Optional: mood (great/good/okay/bad/terrible), entry_date

9. **edit_quest** - Modify existing quest tasks
   - Required: quest_content (to find the quest)
   - Optional: new_content, new_date_due, new_time_due, quest_date
   - Example: "Change my homework task to be due at 5pm"

10. **delete_quest** - Remove quest tasks
   - Required: quest_content
   - Optional: quest_date
   - Example: "Delete my grocery shopping task"

**KNOWLEDGE TOOLS**:

11. **search_internet** - Search for current information, facts, news
   - Required: query
   - Optional: num_results (1-10)
   - Use for questions about current events, facts, how-to info

**BOARD TOOLS** (Secondary focus):

12. **create_board** - Organize projects with Kanban boards
13. **create_card** - Add tasks to existing boards
14. **get_boards** - List user's existing boards

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
1. create_calendar_event(title="Dentist Appointment", start_datetime="{(now + timedelta(days=((1-now.weekday()) % 7) + 7)).strftime('%Y-%m-%d')}T19:00:00Z")
2. Response: "I've scheduled your dentist appointment for Tuesday, [date] at 3:00 PM Eastern."

**TIMEZONE CONVERSION REFERENCE**:
- User says "2 PM" → Create event at "18:00" UTC (2 + 4 = 6 PM UTC)
- User says "9 AM" → Create event at "13:00" UTC (9 + 4 = 1 PM UTC)  
- User says "6 PM" → Create event at "22:00" UTC (6 + 4 = 10 PM UTC)
- User says "noon" → Create event at "16:00" UTC (12 + 4 = 4 PM UTC)

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
        
        user_id = str(user.id)
        
        try:
            # Import execute_ai_tool at the top to avoid scoping issues
            from app.core.ai_tools import execute_ai_tool
            
            # Build conversation messages with system prompt
            messages = [
                {"role": "system", "content": self._get_system_prompt(user)}
            ]
            
            # Add stored conversation history (3 prior exchanges)
            stored_history = self.memory.get_conversation_history(user_id)
            if stored_history:
                messages.extend(stored_history)
            
            # Add any additional conversation history from the request (for compatibility)
            if conversation_history:
                messages.extend(conversation_history[-6:])  # Limit to prevent token overflow
            
            # Check if message contains quest-related keywords and auto-inject quest context
            quest_keywords = [
                'quest', 'quests', 'task', 'tasks', 'todo', 'todos', 'to-do', 'to-dos',
                'complete', 'completed', 'finish', 'finished', 'done', 'did',
                'homework', 'work', 'assignment', 'project', 'chore', 'errand'
            ]
            
            message_lower = message.lower()
            has_quest_context = any(keyword in message_lower for keyword in quest_keywords)
            
            # Auto-inject quest context if quest-related words detected
            enhanced_message = message
            if has_quest_context:
                try:
                    # Get today's quests automatically
                    quest_result = await execute_ai_tool("get_quests", {}, user, session)
                    
                    if quest_result.get("success"):
                        quest_list = quest_result.get("quests", [])
                        
                        if quest_list:
                            quest_context = "\n\n**CURRENT QUEST CONTEXT (automatically provided):**\n"
                            quest_context += f"Today's Quests ({len(quest_list)} total):\n"
                            
                            for i, quest in enumerate(quest_list, 1):
                                status = "✅ COMPLETED" if quest.get("is_complete") else "⏳ PENDING"
                                time_info = ""
                                if quest.get("time_due"):
                                    time_info = f" (due: {quest.get('time_due')})"
                                quest_context += f"{i}. [{status}] {quest.get('content', '')}{time_info}\n"
                            
                            quest_context += f"\nCompleted: {sum(1 for q in quest_list if q.get('is_complete'))}/{len(quest_list)}\n"
                            quest_context += "This context is provided automatically since you mentioned quest-related keywords.\n"
                            
                            enhanced_message = message + quest_context
                        else:
                            enhanced_message = message + "\n\n**QUEST CONTEXT**: No quests found for today."
                    else:
                        logger.warning(f"Failed to auto-fetch quest context: {quest_result.get('error')}")
                except Exception as e:
                    logger.warning(f"Error auto-injecting quest context: {e}")
            
            # Add current user message (potentially enhanced with quest context)
            messages.append({"role": "user", "content": enhanced_message})
            
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
            
            # Store conversation in memory for future context
            # Add user message
            self.memory.add_message(user_id, "user", enhanced_message)
            
            # Add assistant response with tool calls if any
            assistant_tool_calls = None
            if assistant_message.tool_calls:
                assistant_tool_calls = [{
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                } for tool_call in assistant_message.tool_calls]
            
            self.memory.add_message(user_id, "assistant", response_text, assistant_tool_calls)
            
            # Add tool results to memory if there were tool calls
            if assistant_message.tool_calls:
                for i, tool_call in enumerate(assistant_message.tool_calls):
                    if i < len(tool_results):
                        self.memory.add_tool_result(user_id, tool_call.id, tool_results[i]["result"])
            
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
                    "message_count": len(messages),
                    "conversation_length": len(self.memory.get_conversation_history(user_id))
                }
            }
            
        except Exception as e:
            logger.error(f"Error in AI conversation: {e}")
            return {
                "success": False,
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "error": str(e)
            }
    
    def clear_user_conversation(self, user: User):
        """Clear conversation history for a specific user"""
        user_id = str(user.id)
        self.memory.clear_conversation(user_id)
        logger.info(f"Cleared conversation history for user {user_id}")
    
    def get_conversation_stats(self, user: User) -> Dict[str, Any]:
        """Get conversation statistics for a user"""
        user_id = str(user.id)
        history = self.memory.get_conversation_history(user_id)
        return {
            "message_count": len(history),
            "last_activity": self.memory.last_activity.get(user_id),
            "has_context": len(history) > 0
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
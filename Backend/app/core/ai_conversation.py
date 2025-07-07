"""
AI Conversation Handler with OpenAI Integration
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
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
        return f"""You are Skema AI, a helpful assistant integrated into a productivity application. 
        
You help users manage their tasks, schedule events, write journal entries, and organize their work using natural language commands.

Current user: {user.full_name or user.email}

You have access to the following tools:
- create_journal_entry: Create journal entries with title, content, and mood
- create_calendar_event: Schedule events with date, time, and details
- create_board: Create new Kanban boards for organizing projects
- create_card: Add cards to existing boards
- get_boards: List user's existing boards

Guidelines:
1. Always be helpful and concise
2. When users ask to create something, use the appropriate tool
3. Extract relevant information from user requests (dates, times, titles, etc.)
4. If information is missing, ask for clarification
5. Provide feedback after successfully completing actions
6. Be conversational and friendly

Current date and time: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}

Remember to:
- Parse dates and times carefully (handle phrases like "tomorrow", "next week", "2 PM")
- Suggest appropriate moods for journal entries based on content
- Use descriptive titles for boards and cards
- Provide helpful responses even when you can't complete an action
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
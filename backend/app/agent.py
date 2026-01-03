import json
import os
from openai import OpenAI
from app.tools import TOOLS, call_tool, current_user_token

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def run_chat_turn(user_message: str, chat_history: list, oauth_token: str):
    # 1. Inject the token for this specific request
    token_reset = current_user_token.set(oauth_token)

    try:
        # 2. Convert MCP Tools to OpenAI Format
        openai_tools = [{
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema
            }
        } for t in TOOLS]

        # 3. Add user message
        chat_history.append({"role": "user", "content": user_message})

        # 4. First Call (Does AI want to talk or use a tool?)
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=chat_history,
            tools=openai_tools,
            tool_choice="auto"
        )
        
        ai_msg = response.choices[0].message
        
        # CASE A: AI just replies (No tool used)
        if not ai_msg.tool_calls:
            return {
                "role": "assistant",
                "content": ai_msg.content,
                "trace": None 
            }

        # CASE B: AI wants to use a tool
        # We'll execute it and run the loop again
        trace_logs = []
        chat_history.append(ai_msg) # Add the "intent" to history

        for tool_call in ai_msg.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            trace_logs.append(f"> Tool Call: {func_name}({args})")
            
            # EXECUTE THE TOOL via MCP
            result_list = await call_tool(func_name, args)
            result_text = result_list[0].text
            
            trace_logs.append(f"> Result: {result_text}")

            # Feed result back to AI
            chat_history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_text
            })

        # 5. Final Call (AI summarizes the tool result)
        final_response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=chat_history
        )
        
        return {
            "role": "assistant",
            "content": final_response.choices[0].message.content,
            "trace": trace_logs 
        }

    finally:
        # Cleanup context
        current_user_token.reset(token_reset)
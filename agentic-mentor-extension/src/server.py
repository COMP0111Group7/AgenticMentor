import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import ollama

app = FastAPI()

class ChatRequest(BaseModel):
    prompt: str
    workspace: str

async def run_agent_workflow(prompt: str, workspace: str):
    # 1. Provide workspace awareness to the model via system prompt
    system_instruction = (
        "You are an expert AI software engineering agent. "
        f"You are currently operating in the following local workspace path: {workspace}. "
        "Keep answers clear, accurate, and structured with clean markdown."
    )

    yield f"> **Agent initialized** for workspace: `{workspace}`\n\n"

    try:
      # 2. Use the AsyncClient to avoid blocking FastAPI's event loop
      client = ollama.AsyncClient(host="http://127.0.0.1:18434")  # Adjust port if using custom host (e.g. 18434)
      
      # Change model to whatever you have pulled locally (e.g., qwen2.5-coder:7b, llama3.1:8b)
      model_name = "qwen3.6:27b"

      response_stream = await client.chat(
          model=model_name,
          messages=[
              {"role": "system", "content": system_instruction},
              {"role": "user", "content": prompt}
          ],
          stream=True
      )

      # 3. Stream tokens live as Ollama generates them
      async for chunk in response_stream:
          content = chunk.get("message", {}).get("content", "")
          if content:
              yield content

    except Exception as e:
        yield f"\n\n**Ollama Agent Error:** {str(e)}"

@app.post("/chat")
async def chat_endpoint(payload: ChatRequest):
    return StreamingResponse(
        run_agent_workflow(payload.prompt, payload.workspace),
        media_type="text/plain"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
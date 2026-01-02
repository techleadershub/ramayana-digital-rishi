import sys
import os

# Ensure current directory and root are in path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)
sys.path.append(os.path.abspath(os.path.join(base_dir, '..')))

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from deep_agent import agent
# System prompt is now internal to deep_agent, but we can pass query directly

from langchain_core.messages import HumanMessage, SystemMessage
import uvicorn
import os
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI(title="Ramayana Deep Research Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for dev, or specific ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str
    thread_id: str = "default_thread"

@app.get("/health")
def health():
    """Basic health check"""
    return {"status": "ok", "agent": "Digital Rishi"}

@app.get("/health/detailed")
def health_detailed():
    """Detailed health check including Qdrant and collections"""
    from query_ramayana import RamayanaSearcher
    health_status = {
        "status": "ok",
        "agent": "Digital Rishi",
        "qdrant": {"connected": False, "collections": {}},
        "model": {"loaded": False},
        "ingestion": {"status": "unknown", "collections": {}}
    }
    
    try:
        searcher = RamayanaSearcher()
        health_status["model"]["loaded"] = searcher.model is not None
        
        # Check Qdrant collections
        collections = searcher.client.get_collections().collections
        health_status["qdrant"]["connected"] = True
        collection_names = [c.name for c in collections]
        
        # Check required collections with point counts
        required_collections = {
            "verses": searcher.collection_name,
            "sargas": searcher.sarga_collection_name
        }
        
        ingestion_status = "complete"
        for key, collection_name in required_collections.items():
            if collection_name in collection_names:
                try:
                    info = searcher.client.get_collection(collection_name)
                    point_count = info.points_count
                    health_status["qdrant"]["collections"][collection_name] = {
                        "exists": True,
                        "points": point_count
                    }
                    health_status["ingestion"]["collections"][key] = {
                        "name": collection_name,
                        "points": point_count,
                        "status": "ok" if point_count > 0 else "empty"
                    }
                    if point_count == 0:
                        ingestion_status = "incomplete"
                except Exception as e:
                    health_status["qdrant"]["collections"][collection_name] = {
                        "exists": True,
                        "error": str(e)
                    }
                    ingestion_status = "error"
            else:
                health_status["qdrant"]["collections"][collection_name] = {
                    "exists": False
                }
                health_status["ingestion"]["collections"][key] = {
                    "name": collection_name,
                    "status": "missing"
                }
                ingestion_status = "incomplete"
        
        health_status["ingestion"]["status"] = ingestion_status
        
        if ingestion_status != "complete":
            health_status["status"] = "warning"
            health_status["message"] = f"Ingestion status: {ingestion_status}. Some collections may be missing or empty."
            health_status["ingestion"]["instructions"] = "Run: python ingest_ramayana.py && python ingest_sargas.py && python agent_api/ingest.py"
        
    except Exception as e:
        health_status["status"] = "error"
        health_status["error"] = str(e)
    
    return health_status

from tools import get_verse_details

@app.get("/verse")
def get_verse(kanda: str, sarga: int, shloka: int):
    """
    Fetch full details for a specific verse.
    """
    details = get_verse_details(kanda, sarga, shloka)
    if not details:
        raise HTTPException(status_code=404, detail="Verse not found")
    return details

from fastapi import BackgroundTasks

@app.post("/admin/ingest")
async def trigger_ingestion(background_tasks: BackgroundTasks, secret: str = None):
    """
    Trigger the full ingestion pipeline in the background.
    In production, you should pass a secret key.
    """
    from ingest_ramayana import RamayanaIngestor
    from ingest_sargas import ingest_full_sargas
    from ingest import ingest_data as ingest_sql
    # Simple security check if needed
    # if secret != os.environ.get("ADMIN_SECRET"):
    #    raise HTTPException(status_code=403)

    def run_full_pipeline():
        print("Starting Full Production Ingestion...")
        try:
            # 1. SQL Ingestion
            ingest_sql()
            # 2. Sarga Ingestion
            ingest_full_sargas()
            # 3. Verse Ingestion
            ingestor = RamayanaIngestor()
            ingestor.run()
            print("Full Production Ingestion Completed.")
        except Exception as e:
            print(f"Ingestion Failed: {e}")

    background_tasks.add_task(run_full_pipeline)
    return {"message": "Ingestion started in background. This may take 15-20 minutes."}

@app.post("/chat_stream")
async def chat_stream(req: ChatRequest):
    """
    Streams the agent's thought process and final response.
    Events: 'thought' (plans/tool calls), 'answer' (final text).
    """
    print(f"Received Query: {req.query} (ID: {req.thread_id})")
    # Increase recursion limit to 100 (Deep, thorough research)
    config = {"configurable": {"thread_id": req.thread_id}, "recursion_limit": 100}
    
    # For Deep Agent, we pass 'query' in the state directly
    # The 'messages' key is still used for compatibility with the graph state definition
    inputs = {
        "query": req.query, 
        "messages": [("user", req.query)]
    }
    
    async def event_stream():
        # Using aasync generator to stream
        try:
            print("Starting Agent Stream...")
            last_plan = []
            last_idx = 0
            
            async for event in agent.astream(inputs, config, stream_mode="values"):
                # Detect Plan Changes
                current_plan = event.get("plan", [])
                current_idx = event.get("current_step_index", 0)
                
                # If plan has been created/changed
                if current_plan and current_plan != last_plan:
                    print(f"Yielding Plan: {current_plan}")
                    yield json.dumps({"type": "plan", "steps": current_plan, "completed": last_idx}) + "\n"
                    last_plan = current_plan
                
                # If progress made
                if current_idx != last_idx:
                    print(f"Yielding Progress: {current_idx}")
                    yield json.dumps({"type": "plan_update", "completed": current_idx}) + "\n"
                    last_idx = current_idx
                
                if "messages" in event and event["messages"]:
                    last_msg = event["messages"][-1]
                    if hasattr(last_msg, 'type') and last_msg.type == "ai":
                        # Check for tool calls
                        has_tools = hasattr(last_msg, 'tool_calls') and last_msg.tool_calls
                        
                        if last_msg.content:
                            if has_tools:
                                # Content with tools = Reasoning/Thought
                                print(f"Yielding Thought Content (len={len(last_msg.content)})")
                                yield json.dumps({"type": "thought", "content": last_msg.content}) + "\n"
                            else:
                                # Content without tools = Final Answer (only if it's the Synthesizer output)
                                # The Planner also outputs an AIMessage, but we want to show that as a thought/intermediary or hide it?
                                # The user wants to see the PLAN visually. The text version might be redundant.
                                # Let's show it as a thought if it comes from planner.
                                # But how to distinguish?
                                # Helper: "If I have a plan but research_log is empty, I am planner."
                                is_planner_msg = (current_plan and not event.get("research_log"))
                                
                                if is_planner_msg:
                                     # Suppress text output for planner, since we send the visual plan?
                                     # Or send it as thought.
                                     pass
                                else:
                                     print(f"Yielding Answer (len={len(last_msg.content)})")
                                     yield json.dumps({"type": "answer", "content": last_msg.content}) + "\n"

                        if has_tools:
                             # Extract tool names and ARGS
                             tools_info = []
                             for tc in last_msg.tool_calls:
                                 name = tc.get('name', 'unknown')
                                 args = tc.get('args', {})
                                 tools_info.append(f"{name}({args})")
                             
                             tool_str = ", ".join(tools_info)
                             thought_content = f"Invoking: {tool_str}..."
                             print(f"Yielding Tool Call: {thought_content}")
                             yield json.dumps({"type": "thought", "content": thought_content}) + "\n"
                             
                             # Explainable AI: Yield step detail
                             # We map tool names to friendlier text if possible
                             friendly_details = []
                             for tc in last_msg.tool_calls:
                                 name = tc.get('name', '')
                                 args = tc.get('args', {})
                                 
                                 if "search_principles" in name:
                                     friendly_details.append(f"Searching wisdom for '{args.get('query')}'")
                                 elif "search_narrative" in name:
                                     friendly_details.append(f"Searching stories for '{args.get('query')}'")
                                 elif "get_verse_context" in name:
                                     friendly_details.append(f"Reading full context for Verse {args.get('verse_id')}")
                                 else:
                                     friendly_details.append(f"call {name}({args})")
                             
                             for detail in friendly_details:
                                 yield json.dumps({
                                     "type": "step_detail", 
                                     "step_index": current_idx, 
                                     "detail": detail
                                 }) + "\n"
            print("Stream Finished Successfully.")
        except Exception as e:
            print(f"ERROR in Stream: {e}")
            # Check for recursion error
            error_msg = str(e)
            if "Recursion limit" in error_msg:
                friendly_msg = "My deep research is taking longer than expected. Please try refining your query or asking again."
                yield json.dumps({"type": "answer", "content": friendly_msg}) + "\n"
            else:
                yield json.dumps({"type": "error", "content": f"System Error: {str(e)}"}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

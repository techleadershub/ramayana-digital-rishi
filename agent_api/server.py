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
    """Detailed health check including Qdrant and collections - with timeout protection"""
    import threading
    import queue
    
    health_status = {
        "status": "ok",
        "agent": "Digital Rishi",
        "qdrant": {"connected": False, "collections": {}, "error": None},
        "model": {"loaded": False},
        "ingestion": {"status": "unknown", "collections": {}}
    }
    
    # Check model - just verify import works (don't actually load)
    try:
        from sentence_transformers import SentenceTransformer
        health_status["model"]["loaded"] = True
    except Exception as e:
        health_status["model"]["loaded"] = False
        health_status["model"]["error"] = str(e)
    
    # Check Qdrant connection with timeout using threading
    def check_qdrant(result_queue):
        """Check Qdrant connection in a separate thread"""
        try:
            from qdrant_client import QdrantClient
            import yaml
            import os
            
            # Load config
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, '..', 'config.yaml')
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            qdrant_config = config['qdrant']
            mode = os.environ.get("QDRANT_MODE", qdrant_config.get('mode', 'server'))
            host = os.environ.get("QDRANT_HOST", qdrant_config.get('host', 'localhost'))
            port = int(os.environ.get("QDRANT_PORT", qdrant_config.get('port', 6333)))
            qdrant_url = os.environ.get("QDRANT_URL")
            api_key = os.environ.get("QDRANT_API_KEY")
            timeout = int(os.environ.get("QDRANT_TIMEOUT", 30))
            
            # Store connection info for error messages
            connection_info = {}
            if qdrant_url:
                connection_info["type"] = "URL"
                connection_info["value"] = qdrant_url
            else:
                connection_info["type"] = "HOST:PORT"
                connection_info["value"] = f"{host}:{port}"
            
            # Create client with timeout
            if mode == 'local':
                client = QdrantClient(path=qdrant_config.get('path', './qdrant_storage'), timeout=timeout)
            elif qdrant_url:
                client = QdrantClient(url=qdrant_url, api_key=api_key, timeout=timeout)
            else:
                client = QdrantClient(host=host, port=port, api_key=api_key, timeout=timeout)
            
            # Get collections
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            # Check required collections
            verse_collection = qdrant_config['collection_name']
            sarga_collection = qdrant_config.get('sarga_collection_name', 'ramayana_sargas')
            required_collections = {
                "verses": verse_collection,
                "sargas": sarga_collection
            }
            
            result = {
                "connected": True,
                "collections": {},
                "ingestion": {"collections": {}, "status": "complete"}
            }
            
            ingestion_status = "complete"
            for key, collection_name in required_collections.items():
                if collection_name in collection_names:
                    try:
                        info = client.get_collection(collection_name)
                        point_count = info.points_count
                        result["collections"][collection_name] = {
                            "exists": True,
                            "points": point_count
                        }
                        result["ingestion"]["collections"][key] = {
                            "name": collection_name,
                            "points": point_count,
                            "status": "ok" if point_count > 0 else "empty"
                        }
                        if point_count == 0:
                            ingestion_status = "incomplete"
                    except Exception as e:
                        result["collections"][collection_name] = {
                            "exists": True,
                            "error": str(e)
                        }
                        ingestion_status = "error"
                else:
                    result["collections"][collection_name] = {
                        "exists": False
                    }
                    result["ingestion"]["collections"][key] = {
                        "name": collection_name,
                        "status": "missing"
                    }
                    ingestion_status = "incomplete"
            
            result["ingestion"]["status"] = ingestion_status
            result_queue.put(result)
            
        except Exception as e:
            error_msg = str(e)
            # Add connection info to error
            if 'connection_info' in locals():
                error_msg = f"{error_msg} (Trying to connect to {connection_info.get('type')}: {connection_info.get('value')})"
            result_queue.put({
                "connected": False,
                "error": error_msg,
                "collections": {},
                "ingestion": {"status": "unknown", "collections": {}}
            })
    
    # Run Qdrant check with timeout
    result_queue = queue.Queue()
    thread = threading.Thread(target=check_qdrant, args=(result_queue,))
    thread.daemon = True
    thread.start()
    thread.join(timeout=35)  # 35 second timeout (increased for Railway)
    
    if thread.is_alive():
        # Thread is still running - timeout occurred
        health_status["status"] = "error"
        health_status["qdrant"]["connected"] = False
        
        # Get connection info for the error message
        qdrant_url = os.environ.get("QDRANT_URL")
        host = os.environ.get("QDRANT_HOST", "localhost")
        port = os.environ.get("QDRANT_PORT", "6333")
        
        if qdrant_url:
            health_status["qdrant"]["error"] = f"Connection timeout after 35s - Check QDRANT_URL: {qdrant_url}"
        else:
            health_status["qdrant"]["error"] = f"Connection timeout after 35s - Check QDRANT_HOST: {host}:{port}"
            
        health_status["qdrant"]["troubleshooting"] = "Verify QDRANT_HOST/URL is correct and service is running. If using Railway Private Network, ensure the host matches your Qdrant service's private domain."
    else:
        # Thread completed
        try:
            qdrant_result = result_queue.get_nowait()
            health_status["qdrant"] = {
                "connected": qdrant_result.get("connected", False),
                "collections": qdrant_result.get("collections", {}),
                "error": qdrant_result.get("error")
            }
            health_status["ingestion"] = qdrant_result.get("ingestion", {"status": "unknown", "collections": {}})
            
            ingestion_status = health_status["ingestion"].get("status", "unknown")
            if ingestion_status != "complete":
                health_status["status"] = "warning"
                health_status["message"] = f"Ingestion status: {ingestion_status}. Some collections may be missing or empty."
                health_status["ingestion"]["instructions"] = "Run: python ingest_ramayana.py && python ingest_sargas.py && python agent_api/ingest.py"
        except queue.Empty:
            health_status["status"] = "error"
            health_status["qdrant"]["connected"] = False
            health_status["qdrant"]["error"] = "Failed to get Qdrant status"
    
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
async def trigger_ingestion(
    background_tasks: BackgroundTasks, 
    secret: str = None,
    skip_sargas: bool = False,
    skip_sql: bool = False
):
    """
    Trigger the ingestion pipeline in the background.
    Options:
    - skip_sargas: Skip the long Sarga ingestion process.
    - skip_sql: Skip the SQL database population.
    """
    from ingest_ramayana import RamayanaIngestor
    from ingest_sargas import ingest_full_sargas
    from ingest import ingest_data as ingest_sql

    def run_pipeline():
        print("Starting Production Ingestion Pipeline...")
        try:
            # 1. SQL Ingestion
            if not skip_sql:
                print("Step 1: Ingesting SQL Data...")
                ingest_sql()
            else:
                print("Skipping SQL Ingestion.")

            # 2. Sarga Ingestion
            if not skip_sargas:
                print("Step 2: Ingesting Sargas (this may take a while)...")
                ingest_full_sargas()
            else:
                print("Skipping Sarga Ingestion.")

            # 3. Verse Ingestion (Always run unless we add a flag, but user wants this specifically)
            print("Step 3: Ingesting Verses (Shlokas)...")
            ingestor = RamayanaIngestor()
            ingestor.run()
            
            print("Ingestion Pipeline Completed.")
        except Exception as e:
            print(f"Ingestion Failed: {e}")

    background_tasks.add_task(run_pipeline)
    return {
        "message": "Ingestion started in background.", 
        "skipped": {
            "sargas": skip_sargas,
            "sql": skip_sql
        }
    }

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

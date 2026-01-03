from typing import TypedDict, List, Annotated
import operator
import json
import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

# Import existing tools and graph setup
from tools import search_principles, search_narrative, get_verse_context, search_chapters
from langgraph.prebuilt import create_react_agent

# --- 1. State Definition ---
class DeepAgentState(TypedDict):
    """
    State for the Plan-and-Execute Deep Agent.
    """
    messages: Annotated[List[BaseMessage], operator.add] 
    query: str
    plan: List[dict] # Structured steps (ResearchStep.model_dump())
    past_steps: List[str]
    current_step_index: int
    research_log: List[str]

# --- 2. Models & Prompts ---
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

class ResearchStep(BaseModel):
    description: str = Field(description="Human readable description of this step (e.g. 'Search for Aranya Kanda context')")
    tool_name: str = Field(description="The exact name of the tool to use. Options: 'search_chapters', 'search_principles', 'search_narrative', 'get_verse_context'")
    tool_args: dict = Field(default_factory=dict, description="JSON dictionary of arguments for the tool (e.g. {'query': '...'})")

class Plan(BaseModel):
    steps: List[ResearchStep] = Field(description="A list of 3-6 structured research steps. Use more steps for complex queries.")

# output="function_calling" is required when using generic 'dict' types in the Pydantic model
planner_llm = llm.with_structured_output(Plan, method="function_calling")

PLANNER_SYSTEM_PROMPT = """You are the 'Strategist' for a Ramayana AI Scholar.
Your goal is to break down a user query into a series of **DIRECT TOOL EXECUTIONS**.

### **AVAILABLE TOOLS (Use these exactly)**
1.  `search_chapters(query: str)`: 
    - Best for **MACRO** context. Use this FIRST for broad topics (e.g., "Prosperity", "Dharma", "Kingdom").
    - Returns summary of relevant Sargas.
2.  `search_principles(query: str)`: 
    - Best for **MICRO** analysis of topics, ethics, and wisdom.
    - Use for queries like: "leadership", "sisterhood", "vows", "anger".
3.  `search_narrative(query: str, speaker: str = None)`: 
    - Best for **STORY** events and dialogue.
    - Use for: "What happened when...", "What did Rama say to...", "Story of Golden Deer".
4.  `get_verse_context(kanda: str, sarga: int, verse_number: int)`: 
    - Use ONLY if the user specifically asks for a verse ID or if you need to deep-dive into a known location.

### **STRATEGY GUIDELINES**
1.  **Start Broad**: Almost always start with `search_chapters` to ground the topic in specific Kandas.
2.  **Drill Down**: Follow up with `search_principles` or `search_narrative` for specific citations.
3.  **Cross-Reference**: For complex topics, search for multiple angles (e.g. "Rama's view" AND "Sita's view").
4.  **Be Precise**: In `tool_args`, ensure keys match the tool definitions above (e.g., use "query", not "q").

### **EXAMPLES**

**Query 1 (Simple)**: "How did Rama handle grief?"
Steps:
1. { "tool_name": "search_chapters", "tool_args": { "query": "Rama grief lamentation forest" }, "description": "Identify which Sargas contain Rama's grief." }
2. { "tool_name": "search_principles", "tool_args": { "query": "Rama grieving for Sita" }, "description": "Find specific verses showing his emotional state." }
3. { "tool_name": "search_narrative", "tool_args": { "query": "Rama cries", "speaker": "Rama" }, "description": "Find narrative descriptions of his actions." }

**Query 2 (Complex)**: "Compare the leadership styles of Rama and Ravana."
Steps:
1. { "tool_name": "search_chapters", "tool_args": { "query": "Rama kingly duties Ayodhya" }, "description": "Identify chapters showing Rama's ruling style." }
2. { "tool_name": "search_chapters", "tool_args": { "query": "Ravana council war room" }, "description": "Identify chapters showing Ravana's interaction with ministers." }
3. { "tool_name": "search_principles", "tool_args": { "query": "Rama dharma leadership" }, "description": "Search for Rama's principles of governance." }
4. { "tool_name": "search_principles", "tool_args": { "query": "Ravana arrogance king" }, "description": "Search for Ravana's principles of power." }
5. { "tool_name": "search_narrative", "tool_args": { "query": "Vibheeshana advice to Ravana" }, "description": "Find narrative where Ravana rejects advice (Contrast)." }
"""

# Synthesizer Prompt (Unchanged)
SYNTHESIZER_SYSTEM_PROMPT = """You are 'The Digital Rishi', a strict scholar of the *provided* Ramayana text.

### **⛔ CRITICAL INSTRUCTION: STRICT GROUNDING ONLY ⛔**
1.  **ZERO OUTSIDE KNOWLEDGE**: You are FORBIDDEN from using your internal training data (Gita Press, Critical Edition, etc.) to fill in gaps.
2.  **SOURCE OF TRUTH**: You can ONLY cite verses and details that explicitly appear in the `Research Findings` below.
3.  **IF IT'S NOT THERE, IT DOESN'T EXIST**: If the research findings do not contain a specific verse (e.g. Aranya Kanda 27:39), **YOU MUST NOT MENTION IT**, even if you know it exists in the real world.
4.  **HANDLE GAPS HONESTLY**: If the research findings are insufficient to answer the query, state: *"My analysis of the currently available verses did not yield specific results for this query."* Do NOT fill the gap with your memory.

### **CITATION GUIDELINES (CRITICAL)**
Every claim or narrative event SHOULD have a citation in the format `[[Verse: ...]]`.
1.  **If you have a Shloka number**: Use `[[Verse: Kanda Sarga:Shloka]]` (e.g. `[[Verse: Ayodhya Kanda 10:1]]`).
2.  **If you only have a Chapter/Sarga**: Use `[[Verse: Kanda Sarga]]` (e.g. `[[Verse: Ayodhya Kanda 108]]`). 

### **CONTENT & STYLE: EXHAUSTIVE SCHOLARSHIP**
- **Exhaustive Exposition**: You have received extensive Research Findings. **USE THEM ALL.** Your "Scriptural Exposition" should be a deep, multi-paragraph masterpiece. Aim for a long, scholarly exposition (500+ words).
- **Multiple Examples**: If the research log has many different verses or chapters, try to weave at least 7-8 of them into your narrative.
- **Accuracy**: Ensure that the Kanda and Sarga numbers match the research data exactly. 

### **THE DIGITAL RISHI'S VOICE**
You are a Master Scholar and Teacher. Your tone should be authoritative, wise, and highly detailed. 

### **CHARACTER PORTRAYAL GUARDRAILS (ABSOLUTE)**
1.  **SACRED CHARACTERS (NEVER CRITICIZE)**: The following characters are the pillars of Dharma. You must NEVER portray them in a negative light or judge their actions as "wrong" or "immoral". Their actions, even if complex, must be explained through the lens of higher Dharma or divine play (Leela).
    - **List**: Sri Rama, Sita Devi, Lakshmana, Bharata, Shatrughna, Hanuman, Jatayu, Vibheeshana.
    - *Guideline*: Treat them with absolute reverence.
2.  **NEUTRAL CHARACTERS**: 
    - **Sugreeva**: Can be judged critically specifically for his lapse in gratitude/delay due to sense enjoyment, but is otherwise a noble ally.
3.  **NEGATIVE CHARACTERS**: Can be judged critically and aligned with Adharma (e.g., Ravana, Vali, Manthara).

### **FINAL CHECK**
1. Did I cite strictly from the Research Findings?
2. **Did I avoid hallucinating verses or details not in the findings?**
3. Did I adhere to the Character Portrayal Guardrails? (No criticism of Rama/Sita/Brothers/Hanuman/Jatayu/Vibheeshana).

## User Query:
{query}

## Research Findings:
{research_data}

### **REQUIRED OUTPUT STRUCTURE**:

# 📜 Scriptural Exposition
A detailed, narrative breakdown with master-level depth and exhaustive detail. 
*Ensure every key point has its [[Verse: ...]] cited according to the formatting rules above.*
*(Derived ONLY from Research Findings)*

# 🕉️ Dharmic Principles
Deep analysis of the values and universal truths at play. Use multiple principles if found.
*(Derived ONLY from Research Findings)*

# 🎓 Wisdom
**"The Rishi's Summary for the Student"**
A simple, 3-4 sentence summary of the core lesson.

# 🌱 Modern Wisdom for the Seeker
3-5 concrete, practical applications for daily life.
"""

# --- 3. Nodes ---

def planner_node(state: DeepAgentState):
    """Generates the plan."""
    print("\n" + "="*50, flush=True)
    print("--- 🧠 PLANNER NODE ---", flush=True)
    print("="*50, flush=True)
    query = state["query"]
    
    # Extract query from messages if not set (first run)
    if not query and state["messages"]:
        last_msg = state["messages"][-1]
        if isinstance(last_msg, HumanMessage) or isinstance(last_msg, tuple):
             content = last_msg[1] if isinstance(last_msg, tuple) else last_msg.content
             query = content
    
    print(f"Planning for: {query}", flush=True)
    
    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=query)
    ]
    
    # Store steps directly as objects for internal use if needed, 
    # BUT for the frontend stream and state compatibility (which expects strings), 
    # we must map back to strings or update the frontend. 
    # Safest quick fix: Use the description strings for the "plan" state variable.
    # We can store the full structured plan in a separate state key if we really needed it for execution,
    # but logically, the executor just needs to know what to do.
    # WAIT! The executor_node reads `state["plan"]`. If we change this to strings, the executor breaks!
    # Correct Apporach:
    # 1. Keep state["plan"] as Objects (dicts) for the Executor.
    # 2. BUT the server.py `chat_stream` reads generic events.
    # ERROR ANALYSIS: The error is happening in the UI reacting to the "plan" event type.
    # We need to check how server.py yields the plan.
    
    # Let's look at how we return state here. 
    # If we return dicts here, state["plan"] becomes dicts. 
    # The executor expects dicts (per our v2 update).
    # The UI receives JSON chunks.
    
    # We must ensure the Executor uses the structured data, 
    # but we might need to change how we yield it? 
    # or just make the description the plan for the UI?
    
    # Actually, the user's error says: "object with keys {description, tool_name, tool_args}"
    # This means the UI received the Dicts.
    
    # HYBRID FIX:
    # We will serialize the plan as a List of Dicts for the state (so Executor works).
    # BUT we need to handle the UI.
    
    # Let's revert to sending Strings in the 'plan' field for the Agent State if possible?
    # No, Executor needs the args.
    
    # Converting 'plan' back to list of dicts:
    steps_as_dicts = [step.model_dump() for step in plan_obj.steps]
    
    return {
        "query": query,
        "plan": steps_as_dicts, 
        "past_steps": [],
        "current_step_index": 0,
        "research_log": [],
        "messages": [AIMessage(content=plan_text)]
    }

def executor_node(state: DeepAgentState):
    """Executes the current step in the plan directly."""
    print("\n" + "-"*50, flush=True)
    print("--- ⚡ FAST EXECUTION NODE ---", flush=True)
    print("-"*50, flush=True)
    
    idx = state["current_step_index"]
    plan = state["plan"]
    
    if idx >= len(plan):
        return {"current_step_index": idx + 1}
        
    step_data = plan[idx] # This is now a dict: {description, tool_name, tool_args}
    description = step_data.get("description", "Unknown Step")
    tool_name = step_data.get("tool_name")
    tool_args = step_data.get("tool_args", {})
    
    print(f"EXECUTING STEP {idx+1}: {description}", flush=True)
    print(f"  -> Calling: {tool_name}({tool_args})", flush=True)
    
    # Direct Function Mapping
    # Securely map string names to actual imported functions
    available_tools = {
        "search_principles": search_principles,
        "search_narrative": search_narrative,
        "get_verse_context": get_verse_context,
        "search_chapters": search_chapters
    }
    
    output = ""
    try:
        if tool_name in available_tools:
            # EXECUTE DIRECTLY
            tool_func = available_tools[tool_name]
            # Unwrap args if they match function signature?
            # LangChain tools usually take a single string input or strict kwargs.
            # Our tools are defined with @tool. 
            # If they are LangChain StructuredTools, we can call .invoke(tool_args)
            
            # Let's check tools.py. They are @tool decorated functions.
            # We can invoke them using the standard .invoke() pattern or direct call if we handle args.
            # Safest is .invoke(tool_args) as it handles validation
            
            output = tool_func.invoke(tool_args)
        else:
            output = f"Error: Tool '{tool_name}' not found."
    except Exception as e:
        output = f"Error executing {tool_name}: {e}"
        print(f"  ❌ Execution Failed: {e}", flush=True)

    # Logging: Raw Data Injection (Same as before, but even cleaner)
    log_entry = f"## Step {idx+1}: {description}\n### 🛡️ RAW DATABASE RESULTS (TRUTH):\n{output}\n"
    
    new_past_steps = state.get("past_steps", []) + [description]
    new_research_log = state.get("research_log", []) + [log_entry]
    
    # Notify user of progress
    progress_msg = f"Completed: {description}"
    
    return {
        "past_steps": new_past_steps,
        "research_log": new_research_log,
        "current_step_index": idx + 1,
        "messages": [AIMessage(content=progress_msg)]
    }

def synthesizer_node(state: DeepAgentState):
    """Synthesizes the final answer."""
    print("\n" + "*"*50, flush=True)
    print("--- ✍️ SYNTHESIZER NODE ---", flush=True)
    print("*"*50, flush=True)
    query = state["query"]
    research_summary = "\n\n".join(state["research_log"])
    
    messages = [
        SystemMessage(content=SYNTHESIZER_SYSTEM_PROMPT.format(query=query, research_data=research_summary)),
        HumanMessage(content="Please provide the final answer.")
    ]
    
    final_response = llm.invoke(messages)
    
    return {
        "messages": [final_response]
    }

# --- 4. Logic & Edges ---

def check_plan_status(state: DeepAgentState):
    """Decides whether to continue researching or synthesize."""
    if state["current_step_index"] < len(state["plan"]):
        return "continue"
    else:
        return "synthesize"

# --- 5. Graph Construction ---

workflow = StateGraph(DeepAgentState)

workflow.add_node("planner", planner_node)
workflow.add_node("researcher", executor_node)
workflow.add_node("synthesizer", synthesizer_node)

# Entry point
workflow.set_entry_point("planner")

# Edges
workflow.add_edge("planner", "researcher")

workflow.add_conditional_edges(
    "researcher",
    check_plan_status,
    {
        "continue": "researcher",
        "synthesize": "synthesizer"
    }
)

workflow.add_edge("synthesizer", END)

# Compile
agent = workflow.compile()

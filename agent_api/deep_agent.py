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
    plan: List[str]
    past_steps: List[str]
    current_step_index: int
    research_log: List[str]

# --- 2. Models & Prompts ---
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Planner Model
class Plan(BaseModel):
    steps: List[str] = Field(description="A list of 3-5 clear, distinct research steps to answer the user request.")

planner_llm = llm.with_structured_output(Plan)

PLANNER_SYSTEM_PROMPT = """You are the 'Strategist' for a Ramayana AI Scholar.
Your goal is to break down a complex user query into a logical research plan.

### **HIERARCHICAL RESEARCH (CRITICAL)**:
1.  **Macro-to-Micro**: If the user asks a broad thematic question (e.g., 'Prosperity', 'Grief', 'City life'), your first step MUST be to use `search_chapters` to get the big picture.
2.  **Narrowing Down**: Use the chapter summaries to decide which specific Kandas/Sargas to search for verses in.
3.  **Fact-Driven**: Do NOT assume modern interpretations. Search for the root cause in the Valmiki Ramayana text.
4.  **Cross-Reference**: Always include a step to find specific verses using `search_principles` or `search_narrative` *after* you have the chapter context.

### GUIDELINES
1.  **Analyze**: Identify the core *conflict* or *dilemma*.
2.  **Bridge to Archetypes**: Map the modern problem to specific Ramayana episodes.
3.  **Plan Tasks**: Create 3-5 unique, directed research steps.

### EXAMPLES (Study these patterns)
Query: "How was the prosperity in Dasharatha's rule?"
Plan:
[
  "Use search_chapters to get a macro view of Ayodhya's prosperity in Bala Kanda and Ayodhya Kanda",
  "Search for specific verses in Bala Kanda Sarga 6 describing the city's wealth and citizens",
  "Search for descriptions of Rama's rule in Uttara Kanda to compare with Dasharatha's",
  "Synthesize a report on hierarchical prosperity from King to Citizen"
]

### OUTPUT FORMAT
Return ONLY a JSON list of strings.
"""

# Synthesizer Prompt
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
             # Handle potential tuple format from server.py input
             content = last_msg[1] if isinstance(last_msg, tuple) else last_msg.content
             query = content
    
    print(f"Planning for: {query}", flush=True)
    
    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=query)
    ]
    
    plan_obj = planner_llm.invoke(messages)
    
    # Log the plan as an AI message so user sees it
    plan_text = "I have developed a research plan:\n" + "\n".join([f"{i+1}. {step}" for i, step in enumerate(plan_obj.steps)])
    
    return {
        "query": query,
        "plan": plan_obj.steps,
        "past_steps": [],
        "current_step_index": 0,
        "research_log": [],
        "messages": [AIMessage(content=plan_text)]
    }

def executor_node(state: DeepAgentState):
    """Executes the current step in the plan."""
    print("\n" + "-"*50, flush=True)
    print("--- 🕵️ RESEARCHER NODE ---", flush=True)
    print("-"*50, flush=True)
    idx = state["current_step_index"]
    plan = state["plan"]
    
    if idx >= len(plan):
        return {"current_step_index": idx + 1} # Should go to synthesizer
        
    current_task = plan[idx]
    print(f"EXECUTING STEP {idx+1}/{len(plan)}: {current_task}", flush=True)
    print("Starting Deep Search sub-agent...", flush=True)
    
    # We use a mini ReAct agent to solve this specific task
    # SYSTEM PROMPT for the mini-researcher to avoid infinite loops and stay concise
    RESEARCHER_SYSTEM_PROMPT = """You are a focused research assistant for the Valmiki Ramayana.
    1. **ACCURACY OVER SPEED**: When you find a relevant chapter, you MUST look for the specific VERSE NUMBER (Shloka) in the text. 
    2. **REPORT NUMBERS**: In your final summary for a step, always include the Kanda Name, Sarga Number, and Shloka Number (e.g. Ayodhya 10:1) so the Synthesizer can cite it correctly.
    3. **NO GUESSING**: If you cannot find a specific verse or the search returns no results, you MUST report "No relevant verses found for this query". Do NOT invent verses.
    4. **EFFICIENCY**: If a search query returns nothing, try AT MOST 2 variations, then move to the next task."""

    tools = [search_principles, search_narrative, get_verse_context, search_chapters]
    mini_agent = create_react_agent(llm, tools)
    
    # Run mini-agent with an explicit recursion limit
    # We prepend the system prompt directly to the messages for compatibility
    result = mini_agent.invoke(
        {"messages": [SystemMessage(content=RESEARCHER_SYSTEM_PROMPT), HumanMessage(content=current_task)]},
        config={"recursion_limit": 100}
    )
    
    # --- RAW DATA INJECTION ---
    # We capture the RAW output from the tools to ensure 100% fidelity.
    # This prevents the Researcher LLM from prioritizing summary over specific verse IDs.
    tool_outputs = []
    for msg in result["messages"]:
        if isinstance(msg, ToolMessage):
             prefix = f"🔌 TOOL OUTPUT ({msg.name}):"
             tool_outputs.append(f"{prefix}\n{msg.content}")

    agent_response = result["messages"][-1].content
    
    if tool_outputs:
        raw_data_block = "\n\n".join(tool_outputs)
        log_entry = f"## Step {idx+1}: {current_task}\n\n### 🛡️ RAW DATABASE RESULTS (TRUTH):\n{raw_data_block}\n\n### 🤖 Researcher Summary:\n{agent_response}\n"
    else:
        # Fallback if no tools were called (pure reasoning)
        log_entry = f"## Step {idx+1}: {current_task}\nResult: {agent_response}\n"

    new_past_steps = state.get("past_steps", []) + [current_task]
    new_research_log = state.get("research_log", []) + [log_entry]
    
    # Notify user of progress (streamed)
    progress_msg = f"Completed Step {idx+1}: {current_task}"
    
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

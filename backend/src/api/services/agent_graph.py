import os
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langgraph.graph import StateGraph, END
import httpx 

# IMPORT LOGGER
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Initialize LLM 
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Define Agent State
class AgentState(TypedDict):
    question: str 
    original_question: str
    chat_history: List[BaseMessage] 
    generation: str 
    intermediate_steps: list 
    route: str 

logger.info("Initial setup complete. AgentState defined.")

# --- Query Rewriter ---
REWRITE_PROMPT_TEMPLATE = """
Given a chat history and the latest user question which might reference context in the chat history, 
formulate a standalone question/statement which can be understood without the chat history.

**CRITICAL RULES:**
1. **Resolve Pronouns:** Replace "it", "that", "the router", "the product" with the specific product name from history.
2. **Preserve Intent:** - If the user asks a question ("What is the price?"), keep it as a question ("What is the price of X?").
   - If the user states an ACTION ("I want to buy it", "Order this"), keep it as an ACTION ("I want to order X"). 
   - **DO NOT** change an order request into a "How to" question.
     - BAD: "What is the process to buy X?"
     - GOOD: "I want to purchase X."

Chat History:
{chat_history}

User Input: {question}
"""
rewrite_prompt = ChatPromptTemplate.from_template(REWRITE_PROMPT_TEMPLATE)
rewrite_chain = rewrite_prompt | llm | StrOutputParser()

def rewrite_query(state: AgentState) -> AgentState:
    """
    Rewrites the user's question to be standalone based on chat history.
    """
    logger.info("---NODE: rewrite_query---")
    question = state["question"]
    chat_history = state.get("chat_history", [])

    # If no history, no need to rewrite
    if not chat_history:
        return {"original_question": question}

    # Convert history to string for the LLM
    history_str = "\n".join([f"{msg.type.upper()}: {msg.content}" for msg in chat_history[-6:]])
    
    try:
        better_question = rewrite_chain.invoke({"chat_history": history_str, "question": question})
        logger.info(f"Rewrote query: '{question}' -> '{better_question}'")
        return {"question": better_question, "original_question": question}
    except Exception as e:
        logger.error(f"Error rewriting query: {e}", exc_info=True)
        return {"original_question": question}

# --- NODES ---

def query_graph_db(state: AgentState) -> AgentState:
    logger.info("---NODE: query_graph_db (calling API)---")
    question = state["question"]
    intermediate_steps = state.get("intermediate_steps", []) 

    try:
        response = httpx.post(
            f"{API_BASE_URL}/db/graph/query",
            json={"question": question},
            timeout=120.0 
        )
        response.raise_for_status() 
        result = response.json()
        result_text = result.get('result', "Error: No result found.")
        
        no_results_indicators = ["No result found", "Error", "No data", "not found", "No information", "[]"]
        has_results = not any(indicator.lower() in result_text.lower() for indicator in no_results_indicators)
        
        if has_results:
            intermediate_steps.append({"tool": "neo4j_qa", "result": result_text})
        else:
            intermediate_steps.append({"tool": "neo4j_qa", "result": result_text, "no_results": True})

    except Exception as e:
        logger.error(f"Error querying Neo4j service: {e}", exc_info=True)
        intermediate_steps.append({"tool": "neo4j_qa", "error": str(e)})

    return {"intermediate_steps": intermediate_steps}

def query_vector_db(state: AgentState) -> AgentState:
    logger.info("---NODE: query_vector_db (calling API)---")
    question = state["question"]
    intermediate_steps = state.get("intermediate_steps", [])

    try:
        response = httpx.post(
            f"{API_BASE_URL}/db/vector/search", 
            json={"question": question},
            timeout=60.0
        )
        response.raise_for_status() 
        retrieved_docs_str = response.json().get("result", "No relevant information found.")
        
        if not retrieved_docs_str or "No relevant information" in retrieved_docs_str:
             logger.info("Vector DB API returned no documents.")
             intermediate_steps.append({"tool": "vector_db", "result": "No relevant information found in the vector database."})
        else:
             logger.info(f"Vector DB API retrieved: {retrieved_docs_str[:200]}...")
             intermediate_steps.append({"tool": "vector_db", "result": retrieved_docs_str})

    except Exception as e:
        logger.error(f"Error querying Vector DB service: {e}", exc_info=True)
        intermediate_steps.append({"tool": "vector_db", "error": str(e)})

    return {"intermediate_steps": intermediate_steps}

EXTRACTION_PROMPT = """
You are an expert at understanding conversation context. 
Based on the chat history and the latest user input, identify the specific product the user wants to buy.

Rules:
1. Look at the "User's input" first. If the full product name is there, use it.
2. If the input uses "it" or "that", look at the "Chat History" (Assistant messages) to find the last mentioned product.
3. Return ONLY the product name. No extra text.
4. If no product is found, return "None".

Chat History:
{chat_history}

User's input: {question}
"""
extraction_prompt = ChatPromptTemplate.from_template(EXTRACTION_PROMPT)
extraction_chain = extraction_prompt | llm | StrOutputParser()

def prepare_order_form_response(state: AgentState) -> AgentState:
    logger.info("---NODE: prepare_order_form_response---")
    question = state["question"]
    chat_history = state.get("chat_history", [])

    product_context = "None"
    try:
        history_str = "\n".join([f"{msg.type.upper()}: {msg.content}" for msg in chat_history[-6:]])
        product_context = extraction_chain.invoke({"chat_history": history_str, "question": question}).strip()
        product_context = product_context.replace('"', '').replace("'", "")
        if "None" in product_context: product_context = ""
    except Exception as e:
        logger.error(f"Error extracting product context: {e}", exc_info=True)
        product_context = ""

    initial_message = "It sounds like you'd like to place an order. I can help you with that. Please fill out the form below."
    form_signal = {
        "type": "order_form", 
        "message": initial_message, 
        "request_id": f"req_{hash(question)}",
        "prefill_product": product_context 
    }
    
    intermediate_steps = state.get("intermediate_steps", [])
    intermediate_steps.append(form_signal)
    return {"intermediate_steps": intermediate_steps}

# --- ROUTER LOGIC ---
ROUTER_PROMPT_TEMPLATE = """
You are an expert router agent. Your task is to analyze the user's question and choose the correct tool.
Output JSON with keys: "reasoning" and "route".

Routes:

1. 'graph_db': Use this for questions about specific product details, prices, availability, OR general shopping requests.
   - "What routers do you sell?"
   - "How much is the Tenda F3?"
   - "I want to buy a router." (User hasn't picked one yet -> Show options)
   - "I'm looking for a security camera." (User needs options -> Show options)
   - "Show me available options."

2. 'vector_db': Use this for company services, procedures, contact info, or social media content.
   - "What services do you provide?"
   - "How do I contact support?"
   - "What is the process to apply?"

3. 'order_form': Use this ONLY when the user explicitly says they want to BUY or PLACE AN ORDER for a SPECIFIC item found in previous context.
   - "I want to buy the Tenda F3." (Specific Item named)
   - "Place an order for it." (Referring to specific item in history)
   - "Add the Prolink router to my cart."
   - "I'll take the first one."
   
   *CRITICAL RULE:* If the user says "I want to buy a router" (General Category), route to 'graph_db'. Only route to 'order_form' if a specific product model is identified.

4. 'general': Use this for greetings, small talk, or questions about the user's name.
   - "Hello"
   - "Who am I?"

Here is the user's question:
{question}
"""

router_prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT_TEMPLATE)
router_chain = router_prompt | llm | JsonOutputParser()

def route_query(state: AgentState) -> AgentState:
    logger.info("---NODE: route_query---")
    question = state["question"]
    state["intermediate_steps"] = []

    response_json = router_chain.invoke({"question": question})
    route_decision = response_json.get("route", "vector_db")
    logger.info(f"Routing decision: {route_decision}, (Reason: {response_json.get('reasoning', 'N/A')})")

    if route_decision == "graph_db": return {"route": "neo4j", "intermediate_steps": []}
    elif route_decision == "vector_db": return {"route": "vector", "intermediate_steps": []}
    elif route_decision == "order_form": return {"route": "order_form", "intermediate_steps": []} 
    else: return {"route": "general", "intermediate_steps": []}

# --- SYNTHESIS & GENERATION ---

# Specialized Prompt for Pure Conversation With Memory
GENERAL_CONVERSATION_TEMPLATE = """
You are a helpful assistant for SLT-MOBITEL.
The user has asked a general conversational question.

**INSTRUCTIONS:**
1. Check the Chat History.
2. If the user asks a personal question (e.g., "Do you remember my name?", "Who am I?"), answer it from history.
3. If the user greets you ("Hello", "Hi"), return a polite greeting.
4. If the user asks about **Products, Services, Prices, Routers, Internet/Fiber Connections, or Company Details**, you MUST output: SEARCH_REQUIRED.
5. **NEVER** invent product information or answer product questions from your general knowledge.

Chat History:
{chat_history}

User Question: {question}
"""
general_prompt = ChatPromptTemplate.from_template(GENERAL_CONVERSATION_TEMPLATE)
general_chain = general_prompt | llm | StrOutputParser()

# 2. Synthesis Prompt (for DB results)
SYNTHESIS_PROMPT_TEMPLATE = """
You are a helpful AI assistant for SLT-MOBITEL. Answer based ONLY on context.
(Your original synthesis prompt content...)

Chat History:
{chat_history}
Intermediate Steps Context:
{intermediate_steps}
User's Latest Question: {question}
Final Answer:
"""
synthesis_prompt = ChatPromptTemplate.from_template(SYNTHESIS_PROMPT_TEMPLATE)
synthesis_chain = synthesis_prompt | llm | StrOutputParser()

def generate_response(state: AgentState) -> AgentState:
    logger.info("---NODE: generate_response---")
    question = state["question"]
    intermediate_steps = state.get("intermediate_steps", [])
    chat_history = state.get("chat_history", [])
    original_route = state.get("route", "")
    
    response = ""

    # --- Handle General Questions ---
    if original_route == "general":
        history_str = "\n".join([f"{msg.type.upper()}: {msg.content}" for msg in chat_history])
        conversation_result = general_chain.invoke({"chat_history": history_str, "question": question})
        
        if "SEARCH_REQUIRED" not in conversation_result:
            logger.info("Handled as pure conversation (Memory used).")
            response = conversation_result
            updated_history = chat_history + [HumanMessage(content=question), AIMessage(content=response)]
            return {"generation": response, "chat_history": updated_history}
        else:
            logger.info("General query requires external info. Falling back to ChromaDB...")

    # --- FALLBACK / DB LOGIC ---
    if original_route == "general" and not intermediate_steps:
        try:
            resp = httpx.post(f"{API_BASE_URL}/db/vector/search", json={"question": question}, timeout=60.0)
            resp.raise_for_status()
            chroma_result = resp.json().get("result", "No relevant info")
            intermediate_steps.append({"tool": "vector_db_general", "result": chroma_result})
        except Exception as e:
            logger.error(f"Error in general fallback: {e}", exc_info=True)

    neo4j_no_results = any(step.get("tool") == "neo4j_qa" and step.get("no_results") for step in intermediate_steps)
    if neo4j_no_results:
        logger.info("Neo4j empty, trying Chroma fallback...")
        try:
            resp = httpx.post(f"{API_BASE_URL}/db/vector/search", json={"question": question}, timeout=60.0)
            chroma_result = resp.json().get("result", "No relevant info")
            intermediate_steps.append({"tool": "vector_db_fallback", "result": chroma_result})
        except: pass

    # --- FINAL SYNTHESIS ---
    context_str = "\n".join([str(step) for step in intermediate_steps])
    history_str = "\n".join([f"{msg.type.upper()}: {msg.content}" for msg in chat_history])
    final_input_question = state.get("original_question", question)

    final_answer = synthesis_chain.invoke({
        "question": final_input_question,
        "intermediate_steps": context_str,
        "chat_history": history_str 
    })
    
    # --- ORDER FORM FORCE ---
    order_signal = next((step for step in intermediate_steps if isinstance(step, dict) and step.get("type") == "order_form"), None)
    
    if order_signal:
        logger.info("Appending forced Order Form signal to response.")
        req_id = order_signal.get("request_id", "req_000")
        prefill = order_signal.get("prefill_product", "")
        
        if prefill:
            final_answer += f"\n\n[SHOW_ORDER_FORM:{req_id}|{prefill}]"
        else:
            final_answer += f"\n\n[SHOW_ORDER_FORM:{req_id}]"

    logger.info(f"Generated final answer: {final_answer}")
    updated_history = chat_history + [HumanMessage(content=final_input_question), AIMessage(content=final_answer)]
    return {"generation": final_answer, "chat_history": updated_history, "intermediate_steps": intermediate_steps}

# --- GRAPH BUILD ---
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("rewrite", rewrite_query)
workflow.add_node("router", route_query)
workflow.add_node("query_neo4j", query_graph_db)
workflow.add_node("query_vector", query_vector_db)
workflow.add_node("prepare_order", prepare_order_form_response)
workflow.add_node("generate", generate_response)

# Set Entry Point
workflow.set_entry_point("rewrite")

# Define Edges
workflow.add_edge("rewrite", "router") 

def decide_next_node(state: AgentState):
    logger.info(f"---DECISION: Based on route '{state['route']}'---")
    if state['route'] == "neo4j": return "query_neo4j"
    elif state['route'] == "vector": return "query_vector"
    elif state['route'] == "order_form": return "prepare_order" 
    elif state['route'] == "general": return "generate"  
    else: return END

workflow.add_conditional_edges(
    "router",     
    decide_next_node,   
    {
        "query_neo4j": "query_neo4j", 
        "query_vector": "query_vector",
        "prepare_order": "prepare_order",
        "generate": "generate",
        END: END                    
    }
)

workflow.add_edge("query_neo4j", "generate")
workflow.add_edge("query_vector", "generate")
workflow.add_edge("prepare_order", "generate")
workflow.add_edge("generate", END)

app = workflow.compile()
logger.info("Graph compiled successfully!")
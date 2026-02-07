import os
from typing import TypedDict, List, Optional
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langgraph.graph import StateGraph, END
import httpx 

# IMPORT LOGGER
from src.utils.logging_config import get_logger

# IMPORT TOOLS
from src.api.services.tools import check_stock_tool

logger = get_logger(__name__)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Initialize LLM 
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# --- Agent State ---
class AgentState(TypedDict):
    question: str 
    original_question: str
    chat_history: List[BaseMessage] 
    generation: str 
    intermediate_steps: list 
    route: str
    user_id: Optional[int]

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

Chat History:
{chat_history}

User Input: {question}
"""
rewrite_prompt = ChatPromptTemplate.from_template(REWRITE_PROMPT_TEMPLATE)
rewrite_chain = rewrite_prompt | llm | StrOutputParser()

def rewrite_query(state: AgentState) -> AgentState:
    logger.info("---NODE: rewrite_query---")
    question = state["question"]
    chat_history = state.get("chat_history", [])

    if not chat_history:
        return {"original_question": question}

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
             intermediate_steps.append({"tool": "vector_db", "result": "No relevant information found."})
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
2. If the input uses "it" or "that", look at the "Chat History" to find the last mentioned product.
3. Return ONLY the product name. No extra text.
4. If no product is found, return "None".

Chat History:
{chat_history}

User's input: {question}
"""
extraction_prompt = ChatPromptTemplate.from_template(EXTRACTION_PROMPT)
extraction_chain = extraction_prompt | llm | StrOutputParser()

# --- SMART ORDER NODE ---
def prepare_order_form_response(state: AgentState) -> AgentState:
    logger.info("---NODE: prepare_order_form_response---")
    
    # 1. PERMISSION CHECK
    user_id = state.get("user_id")
    if not user_id:
        logger.warning("Order attempted without user_id. Blocking.")
        return {
            "intermediate_steps": state.get("intermediate_steps", []) + [{
                "type": "auth_error", 
                "message": "Please log in or register to place an order."
            }]
        }

    question = state["question"]
    chat_history = state.get("chat_history", [])
    intermediate_steps = state.get("intermediate_steps", [])

    # 2. EXTRACT PRODUCT
    product_context = "None"
    try:
        history_str = "\n".join([f"{msg.type.upper()}: {msg.content}" for msg in chat_history[-6:]])
        product_context = extraction_chain.invoke({"chat_history": history_str, "question": question}).strip()
        product_context = product_context.replace('"', '').replace("'", "")
        if "None" in product_context: product_context = ""
    except Exception as e:
        logger.error(f"Error extracting product context: {e}", exc_info=True)
        product_context = ""

    # 3. SAFETY: If no product extracted, DO NOT show form. Ask for clarification.
    if not product_context:
        logger.warning("Could not extract specific product for order.")
        return {
            "intermediate_steps": intermediate_steps + [{
                "type": "stock_error",
                "message": "I'm not sure which product you want to order. Could you please specify the name?"
            }]
        }

    # 4. STOCK CHECK (Smart Agent)
    # We now have a product name, so we check stock.
    stock_status = check_stock_tool.invoke(product_context)
    logger.info(f"DEBUG: Stock Tool Output for '{product_context}': {stock_status}") # <--- DEBUG LOG
    
    # Check for failure keywords from tools.py
    if "UNAVAILABLE" in stock_status or "Error" in stock_status or "not found" in stock_status.lower():
            logger.info(f"Stock check failed: {stock_status}")
            
            user_msg = f"I'm sorry, but {product_context} appears to be out of stock."
            if "not found" in stock_status.lower():
                user_msg = f"I couldn't find a product named '{product_context}' in our catalog."
                
            return {
            "intermediate_steps": intermediate_steps + [{
                "type": "stock_error",
                "message": user_msg
            }]
            }
    
    # 5. SUCCESS SIGNAL
    # Use the product name from the Stock Tool if possible (it corrects the name), otherwise use extracted.
    # The stock tool output format is "AVAILABLE: Product 'Exact Name'..."
    final_product_name = product_context
    if "Product '" in stock_status:
        try:
            # Extract distinct name from tool output: "Product 'Name' (ID..."
            start = stock_status.find("Product '") + 9
            end = stock_status.find("'", start)
            if start > 8 and end > start:
                final_product_name = stock_status[start:end]
        except: pass

    initial_message = f"I can help you place an order for the {final_product_name}. Please confirm the details below."
    form_signal = {
        "type": "order_form", 
        "message": initial_message, 
        "request_id": f"req_{hash(question)}",
        "prefill_product": final_product_name 
    }
    
    intermediate_steps.append(form_signal)
    return {"intermediate_steps": intermediate_steps}

# --- ROUTER LOGIC ---
ROUTER_PROMPT_TEMPLATE = """
You are an expert router agent.
Output JSON with keys: "reasoning" and "route".

Routes:
1. 'graph_db': Product details, prices, availability, or general shopping ("Show me routers").
2. 'vector_db': Services, contact info, procedures.
3. 'order_form': ONLY when user explicitly wants to BUY/ORDER a SPECIFIC item found in context.
4. 'general': Greetings, small talk.

User Question: {question}
"""
router_prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT_TEMPLATE)
router_chain = router_prompt | llm | JsonOutputParser()

def route_query(state: AgentState) -> AgentState:
    logger.info("---NODE: route_query---")
    question = state["question"]
    state["intermediate_steps"] = []

    response_json = router_chain.invoke({"question": question})
    route_decision = response_json.get("route", "vector_db")
    logger.info(f"Routing decision: {route_decision}")

    if route_decision == "graph_db": return {"route": "neo4j", "intermediate_steps": []}
    elif route_decision == "vector_db": return {"route": "vector", "intermediate_steps": []}
    elif route_decision == "order_form": return {"route": "order_form", "intermediate_steps": []} 
    else: return {"route": "general", "intermediate_steps": []}

# --- SYNTHESIS & GENERATION ---
GENERAL_CONVERSATION_TEMPLATE = """
You are a helpful assistant for SLT-MOBITEL.
Instructions:
1. If greeting, greet back.
2. If asking about products/services, output: SEARCH_REQUIRED.
3. Otherwise, answer from history.

Chat History:
{chat_history}
User Question: {question}
"""
general_prompt = ChatPromptTemplate.from_template(GENERAL_CONVERSATION_TEMPLATE)
general_chain = general_prompt | llm | StrOutputParser()

# --- UPDATED SYNTHESIS PROMPT (FIX DOUBLE FORM) ---
SYNTHESIS_PROMPT_TEMPLATE = """
You are a helpful AI assistant for SLT-MOBITEL. Answer based ONLY on context.

**CRITICAL INSTRUCTION:** If the context contains an "order_form" signal, simply reply with a polite confirmation message (e.g., "Sure, I can help with that.").
**DO NOT** generate the tag [SHOW_ORDER_FORM:...] in your output text. The system will add it automatically.

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
            updated_history = chat_history + [HumanMessage(content=question), AIMessage(content=conversation_result)]
            return {"generation": conversation_result, "chat_history": updated_history}
        
    # --- FALLBACK / DB LOGIC ---
    neo4j_no_results = any(step.get("tool") == "neo4j_qa" and step.get("no_results") for step in intermediate_steps)
    if (original_route == "general" and not intermediate_steps) or neo4j_no_results:
        try:
            resp = httpx.post(f"{API_BASE_URL}/db/vector/search", json={"question": question}, timeout=60.0)
            chroma_result = resp.json().get("result", "No relevant info")
            intermediate_steps.append({"tool": "vector_db_fallback", "result": chroma_result})
        except: pass

    # --- CHECK FOR ERRORS (Auth/Stock) ---
    auth_error = next((step for step in intermediate_steps if isinstance(step, dict) and step.get("type") == "auth_error"), None)
    stock_error = next((step for step in intermediate_steps if isinstance(step, dict) and step.get("type") == "stock_error"), None)

    if auth_error:
        final_answer = auth_error["message"]
    elif stock_error:
        final_answer = stock_error["message"]
    else:
        # --- FINAL SYNTHESIS ---
        context_str = "\n".join([str(step) for step in intermediate_steps])
        history_str = "\n".join([f"{msg.type.upper()}: {msg.content}" for msg in chat_history])
        
        final_answer = synthesis_chain.invoke({
            "question": state.get("original_question", question),
            "intermediate_steps": context_str,
            "chat_history": history_str 
        })
        
        # --- ORDER FORM FORCE (Python side only) ---
        order_signal = next((step for step in intermediate_steps if isinstance(step, dict) and step.get("type") == "order_form"), None)
        
        if order_signal:
            logger.info("Appending forced Order Form signal to response.")
            req_id = order_signal.get("request_id", "req_000")
            prefill = order_signal.get("prefill_product", "")
            
            # Append signal cleanly
            final_answer += f"\n\n[SHOW_ORDER_FORM:{req_id}|{prefill}]"

    logger.info(f"Generated final answer: {final_answer}")
    updated_history = chat_history + [HumanMessage(content=state.get("original_question", question)), AIMessage(content=final_answer)]
    return {"generation": final_answer, "chat_history": updated_history, "intermediate_steps": intermediate_steps}

# --- GRAPH BUILD (Unchanged) ---
workflow = StateGraph(AgentState)
workflow.add_node("rewrite", rewrite_query)
workflow.add_node("router", route_query)
workflow.add_node("query_neo4j", query_graph_db)
workflow.add_node("query_vector", query_vector_db)
workflow.add_node("prepare_order", prepare_order_form_response)
workflow.add_node("generate", generate_response)
workflow.set_entry_point("rewrite")
workflow.add_edge("rewrite", "router") 
def decide_next_node(state: AgentState):
    if state['route'] == "neo4j": return "query_neo4j"
    elif state['route'] == "vector": return "query_vector"
    elif state['route'] == "order_form": return "prepare_order" 
    elif state['route'] == "general": return "generate"  
    else: return END
workflow.add_conditional_edges("router", decide_next_node, {"query_neo4j":"query_neo4j", "query_vector":"query_vector", "prepare_order":"prepare_order", "generate":"generate", END:END})
workflow.add_edge("query_neo4j", "generate")
workflow.add_edge("query_vector", "generate")
workflow.add_edge("prepare_order", "generate")
workflow.add_edge("generate", END)
app = workflow.compile()
logger.info("Graph compiled successfully!")
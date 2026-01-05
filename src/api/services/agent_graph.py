import os
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langgraph.graph import StateGraph, END
import httpx 

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Default to localhost for local testing, but allow Docker to override it
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Initialize LLM 
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Define Agent State
class AgentState(TypedDict):
    question: str 
    chat_history: List[BaseMessage] 
    generation: str 
    intermediate_steps: list 
    route: str 

print("Initial setup complete. AgentState defined.")

# Define Nodes 

# query_graph_db Node
def query_graph_db(state: AgentState) -> AgentState:
    """
    Queries the Neo4j SERVICE API based on the question.
    """
    print("---NODE: query_graph_db (calling API)---", flush=True)
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
        
        # Check if the result contains no relevant information
        no_results_indicators = [
            "No result found", 
            "Error", 
            "No data", 
            "not found", 
            "No information",
            "[]"
        ]
        
        has_results = not any(indicator.lower() in result_text.lower() for indicator in no_results_indicators)
        
        if has_results:
            intermediate_steps.append({"tool": "neo4j_qa", "result": result_text})
        else:
            intermediate_steps.append({
                "tool": "neo4j_qa", 
                "result": result_text,
                "no_results": True
            })

    except Exception as e:
        print(f"Error querying Neo4j service: {e}")
        intermediate_steps.append({"tool": "neo4j_qa", "error": str(e)})

    return {"intermediate_steps": intermediate_steps}

print("Node 'query_graph_db' defined (API call version).")

# query_vector_db Node
def query_vector_db(state: AgentState) -> AgentState:
    """
    Queries the vector database (Chroma DB) SERVICE API.
    """
    print("---NODE: query_vector_db (calling API)---", flush=True)
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
             print("Vector DB API returned no documents.")
             intermediate_steps.append({"tool": "vector_db", "result": "No relevant information found in the vector database."})
        else:
             print(f"Vector DB API retrieved: {retrieved_docs_str[:200]}...")
             intermediate_steps.append({"tool": "vector_db", "result": retrieved_docs_str})

    except Exception as e:
        print(f"Error querying Vector DB service: {e}")
        intermediate_steps.append({"tool": "vector_db", "error": str(e)})

    return {"intermediate_steps": intermediate_steps}

print("Node 'query_vector_db' defined (API call version).")

# Extraction chain for the order node
EXTRACTION_PROMPT = """
You are an expert at understanding conversation context. 
Based on the chat history, identify the specific product the user wants to buy.
If the user says "I want to buy that" or similar, look at the previous assistant messages to find the product name.
Return ONLY the product name. If no specific product is mentioned or clear from context, return "None".

Chat History:
{chat_history}

User's input: {question}
"""
extraction_prompt = ChatPromptTemplate.from_template(EXTRACTION_PROMPT)
extraction_chain = extraction_prompt | llm | StrOutputParser()

def prepare_order_form_response(state: AgentState) -> AgentState:
    """
    Prepares a special response that signals the frontend to display the order form.
    It now also attempts to extract the product name from context to pre-fill the form.
    """
    print("---NODE: prepare_order_form_response---", flush=True)
    question = state["question"]
    chat_history = state.get("chat_history", [])

    # Attempt to extract the product name from context
    product_context = "None"
    try:
        # Convert chat history to string for the extraction chain
        history_str = "\n".join([f"{msg.type.upper()}: {msg.content}" for msg in chat_history[-6:]]) # Look at last 6 messages
        product_context = extraction_chain.invoke({"chat_history": history_str, "question": question}).strip()
        
        # Cleanup
        product_context = product_context.replace('"', '').replace("'", "")
        if "None" in product_context: 
            product_context = ""
        else:
            print(f"Extracted product context: {product_context}")
    except Exception as e:
        print(f"Error extracting product context: {e}")
        product_context = ""

    initial_message = "It sounds like you'd like to place an order. I can help you with that. Please fill out the form below."

    # Create the special response structure with the product info
    form_signal = {
        "type": "order_form", 
        "message": initial_message, 
        "request_id": f"req_{hash(question)}",
        "prefill_product": product_context 
    }

    intermediate_steps = state.get("intermediate_steps", [])
    intermediate_steps.append(form_signal)

    return {"intermediate_steps": intermediate_steps}

# Define Router Logic
ROUTER_PROMPT_TEMPLATE = """
You are an expert router agent. Your task is to analyze the user's question and choose the correct tool to answer it.
You must output a JSON object with two keys: "reasoning" and "route".

The "route" key must be one of three values:

1. 'graph_db': Use this for questions about specific product details, prices, categories, features, counts, or relationships.
   This includes ANY question asking for specific product information, prices, or comparing products.
   Examples:
   - "What's the price of X?"
   - "How many Y products are there?"
   - "What category is Z in?"
   - "What router options do I have?"
   - "Show me your security cameras."
   - "Do you have any Tenda routers?"
   - "List all products"

2. 'vector_db': Use this for questions about company services, procedures, website content, social media posts, customer feedback, engagement metrics, or general company information that would be found on websites or social media.
   This includes questions about how to do something, what services are offered, company information from scraped sources, or general company details.
   Examples:
   - "What services do you provide?"
   - "How to get a fiber connection?"
   - "What are recent comments about our service?"
   - "Tell me about the company's mission."
   - "What's on your website about broadband?"
   - "What are your internet packages?"
   - "How to apply for services?"
   - "What are your business solutions?"

3. 'order_form': Use this for questions expressing a clear intent to purchase a product, place an order, or buy something specific from the company's product catalog.
   This includes ANY question indicating the user wants to initiate a purchase process, asks about buying products in the graph_db , or specifically names a product they wish to purchase.
   Examples:
   - "I want to buy a router."
   - "Place an order for the Tenda MX3."
   - "I'd like to purchase the Prolink HCD130C CLI Telephone."
   - "How can I buy the security camera?"
   - "Can you help me order?"
   - "I need to place an order."
   - "Buy Tenda Mx3 2 Pack Mesh Wi-Fi 6 System"
   - "Order ProLink DS-3103"

4. 'general': Use this for conversational questions, greetings, small talk, or questions that don't require database lookups.
   Examples:
   - "Hello"
   - "Hi"
   - "How are you?"
   - "Thanks"
   - "Good morning"
   - "What can you help me with?"

Here is the user's question:
{question}
"""
router_prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT_TEMPLATE)
router_chain = router_prompt | llm | JsonOutputParser()
print("Router chain created (JSON Output).")

def route_query(state: AgentState) -> AgentState:
    """
    Determines whether to query the graph database, vector database, order form or handle as general question AND clears old intermediate steps from previous turns.
    """
    print("---NODE: route_query---", flush=True)
    question = state["question"]

    state["intermediate_steps"] = []

    response_json = router_chain.invoke({"question": question})
    route_decision = response_json.get("route", "vector_db")
    
    print(f"Routing decision: {route_decision}, (Reason: {response_json.get('reasoning', 'N/A')})")

    if route_decision == "graph_db":
        return {"route": "neo4j", "intermediate_steps": []}
    elif route_decision == "vector_db":
        return {"route": "vector", "intermediate_steps": []}
    elif route_decision == "order_form": 
        return {"route": "order_form", "intermediate_steps": []} 
    else:
        return {"route": "general", "intermediate_steps": []}
        
print("Node 'route_query' defined.")


SYNTHESIS_PROMPT_TEMPLATE = """
You are a helpful AI assistant for SLT-MOBITEL. Your job is to answer the user's question based ONLY on the context provided in "Intermediate Steps Context" and the "Chat History".

IMPORTANT RULES:
1. NEVER use your general knowledge to answer questions.
2. If all contexts say "No relevant information found", respond with "I'm sorry, I could not find any specific information about that in our knowledge base."
3. NEVER generate responses about unrelated topics (like dietary fiber when asked about internet fiber products).
4. If Neo4j has no product results but ChromaDB has company/service information, use the ChromaDB information.
5. If the "Intermediate Steps Context" contains multiple entries with identical or very similar content (e.g., the same social media post repeated), consolidate them into a single entry in the final response. Do not list the same post multiple times with different numbers.

For handling specific data source signals in context:
- If you see an entry with "type": "order_form" in the "Intermediate Steps Context", this means the system is preparing to display an order form. 
- Respond with the "message" field from that entry.
- Append a special marker at the end.
- The marker format is: [SHOW_ORDER_FORM:request_id|product_name]
- If "prefill_product" is empty or missing, just use [SHOW_ORDER_FORM:request_id]
- Example 1 (Product found): "It sounds like you want to order... [SHOW_ORDER_FORM:req_123|Prolink DL 7202]"
- Example 2 (No product): "It sounds like you want to order... [SHOW_ORDER_FORM:req_123]"

For handling multiple data sources in context (when NOT an order_form signal):
- If you see "vector_db_general" tool results, these contain company/service information from website/social media
- If you see "vector_db_fallback" tool results, these contain additional company information when Neo4j was empty
- If you see "neo4j_qa" results, these contain specific product information

For questions about SLT products:
- If the user asked a general question like "what products do you have" or "what products do you sell" and Neo4j returned multiple products, DO NOT list all products. Instead, respond with: "We have products from various categories including [list some sample categories like Wi-Fi Devices, Power Backups, Telephones, Routers, etc.]. What type of product are you interested in?"
- If the user asked for specific products (like "routers", "telephones", etc.) and Neo4j returned relevant products, format them nicely with names, prices, and links
- Use Neo4j product information when available for specific product queries
- If Neo4j has no results, use any ChromaDB company information about products/services
- If no product information exists, respond with: "I couldn't find specific information about [product type] in our current product database. You may want to check our official website or contact our customer service for the most up-to-date information."

For questions about SLT services and procedures:
- Use ChromaDB information about company services, procedures, and website content
- Format service information clearly and provide any mentioned contact details or website links

For questions about engagement metrics (comments, reactions, shares, likes):
- Look for documents with metadata containing: likes_count, shares_count, comments_count, reactions_count
- Extract metrics from the metadata, not the content
- Format as: "Post: [post summary] - Likes: [count], Shares: [count], Comments: [count], Reactions: [count]"
- If specific counts are not available, say so explicitly

When showing social media content:
- For posts: "[post content] - from [source]"
- For engagement: "Engagement metrics: [likes] likes, [shares] shares, [comments] comments, [reactions] reactions"

Chat History (most recent at bottom):
{chat_history}

Intermediate Steps Context:
{intermediate_steps}

User's Latest Question: {question}

Final Answer:
"""
synthesis_prompt = ChatPromptTemplate.from_template(SYNTHESIS_PROMPT_TEMPLATE)
synthesis_chain = synthesis_prompt | llm | StrOutputParser()
print("Synthesis chain created.")

def generate_response(state: AgentState) -> AgentState:
    """
    Generates the final response using LLM based on chat history and intermediate steps.
    For greetings, responds directly. For other general questions, queries ChromaDB first. 
    If Neo4j returns no results, queries ChromaDB as fallback.
    """
    print("---NODE: generate_response---", flush=True)
    question = state["question"]
    intermediate_steps = state.get("intermediate_steps", [])
    chat_history = state.get("chat_history", [])
    
    # Check if this is a general question
    original_route = state.get("route", "")
    
    # Handle greetings directly without querying databases
    if original_route == "general":
        if any(greeting in question.lower() for greeting in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
            response = "Hello! I'm your SLT-MOBITEL assistant. How can I help you today? You can ask me about our products, services, or general company information."
        elif any(thanks in question.lower() for thanks in ["thank", "thanks", "thank you"]):
            response = "You're welcome! Is there anything else I can help you with?"
        elif any(ability in question.lower() for ability in ["what can you", "what do you", "how can you", "help"]):
            response = "I can help you with information about SLT-MOBITEL products and services. You can ask about specific product prices, categories, features, or general company information from our website and social media."
        else:
            # For other general questions, query ChromaDB for company information
            print("General question detected, querying ChromaDB for company information...")
            try:
                response = httpx.post(
                    f"{API_BASE_URL}/db/vector/search", 
                    json={"question": question},
                    timeout=60.0
                )
                response.raise_for_status()
                
                chroma_result = response.json().get("result", "No relevant information found.")
                if "No relevant information" not in chroma_result:
                    # Add ChromaDB result as context for general question
                    intermediate_steps.append({"tool": "vector_db_general", "result": chroma_result})
                    print(f"ChromaDB found for general question: {chroma_result[:100]}...")
                else:
                    print("ChromaDB returned no relevant information for general question.")
                    # For general questions with no results, provide a helpful response
                    response = "I'm here to help you with information about SLT-MOBITEL products and services. You can ask about specific products, prices, or general company information."
                    updated_history = chat_history + [HumanMessage(content=question), AIMessage(content=response)]
                    return {"generation": response, "chat_history": updated_history, "intermediate_steps": intermediate_steps}
            except Exception as e:
                print(f"Error querying ChromaDB for general question: {e}")
                response = "I'm here to help you with information about SLT-MOBITEL products and services. You can ask about specific products, prices, or general company information."
                updated_history = chat_history + [HumanMessage(content=question), AIMessage(content=response)]
                return {"generation": response, "chat_history": updated_history, "intermediate_steps": intermediate_steps}
    
    # Check if Neo4j returned no results for a product query
    neo4j_no_results = False
    for step in intermediate_steps:
        if (step.get("tool") == "neo4j_qa" and 
            step.get("no_results", False)):
            neo4j_no_results = True
            break
    
    # If Neo4j had no results, query ChromaDB as fallback
    if neo4j_no_results:
        print("Neo4j returned no results, querying ChromaDB as fallback...")
        try:
            response = httpx.post(
                f"{API_BASE_URL}/db/vector/search", 
                json={"question": question},
                timeout=60.0
            )
            response.raise_for_status()
            
            chroma_result = response.json().get("result", "No relevant information found.")
            if "No relevant information" not in chroma_result:
                # Add ChromaDB result as additional context
                intermediate_steps.append({"tool": "vector_db_fallback", "result": chroma_result})
                print(f"ChromaDB fallback found: {chroma_result[:100]}...")
            else:
                print("ChromaDB also returned no relevant information.")
        except Exception as e:
            print(f"Error querying ChromaDB fallback: {e}")
    
    # Only run synthesis if we have intermediate steps or this isn't a direct response
    if original_route != "general" or not any(greeting in question.lower() for greeting in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "thank", "thanks", "what can you", "what do you", "how can you", "help"]):
        context_str = "\n".join([str(step) for step in intermediate_steps])
        history_str = "\n".join([f"{msg.type.upper()}: {msg.content}" for msg in chat_history])

        final_answer = synthesis_chain.invoke({
            "question": question,
            "intermediate_steps": context_str,
            "chat_history": history_str 
        })
        print(f"Generated final answer: {final_answer}")
        response = final_answer
    
    updated_history = chat_history + [HumanMessage(content=question), AIMessage(content=response)]
    return {"generation": response, "chat_history": updated_history, "intermediate_steps": intermediate_steps}
print("Node 'generate_response' defined.") 

# Build and Compile the Graph
from langgraph.graph import StateGraph, END

print("Building the LangGraph graph...")
workflow = StateGraph(AgentState)
workflow.add_node("router", route_query)
workflow.add_node("query_neo4j", query_graph_db)
workflow.add_node("query_vector", query_vector_db)
workflow.add_node("prepare_order", prepare_order_form_response)
workflow.add_node("generate", generate_response)
workflow.set_entry_point("router")

def decide_next_node(state: AgentState):
    print(f"---DECISION: Based on route '{state['route']}'---", flush=True)
    if state['route'] == "neo4j":
        return "query_neo4j"
    elif state['route'] == "vector":
        return "query_vector"
    elif state['route'] == "order_form": 
        return "prepare_order" 
    elif state['route'] == "general":
        return "generate"  
    else:
        print("Conditional edge fallback: ending.")
        return END

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
print("Graph compiled successfully!")
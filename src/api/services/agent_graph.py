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

API_BASE_URL = "http://localhost:8000" 

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
    print("---NODE: query_graph_db (calling API)---")
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
        intermediate_steps.append({"tool": "neo4j_qa", "result": result['result']})

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
    print("---NODE: query_vector_db (calling API)---")
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

# Define Router Logic
ROUTER_PROMPT_TEMPLATE = """
You are an expert router agent. Your task is to analyze the user's question and choose the correct tool to answer it.
You must output a JSON object with two keys: "reasoning" and "route".

The "route" key must be one of three values:
1. 'graph_db': Use this for questions about specific product details, prices, categories, features, counts, or relationships.
   This includes ANY question asking for a list of products, product options, or product attributes.
   Examples:
   - "What's the price of X?"
   - "How many Y products are there?"
   - "What category is Z in?"
   - "What router options do I have?"
   - "Show me your security cameras."
   - "Do you have any Tenda routers?"

2. 'vector_db': Use this for general, open-ended, or semantic questions about company information, website content, social media posts, customer feedback, engagement metrics (comments, shares, reactions, likes), or comparisons not based on structured attributes.
   Examples:
   - "What are recent comments about our service?"
   - "Summarize our latest blog post."
   - "Give me info on fiber products."
   - "Tell me about the company's mission."
   - "What's the latest news on LinkedIn?"
   - "How many shares and reactions do our posts have?"
   - "What are the engagement metrics for SLT posts?"
   - "Show me recent social media activity."

3. 'general': Use this for conversational questions, greetings, small talk, or questions that don't require database lookups.
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
    Determines whether to query the graph database, vector database, or handle as general question.
    """
    print("---NODE: route_query---")
    question = state["question"]

    response_json = router_chain.invoke({"question": question})
    route_decision = response_json.get("route", "vector_db")
    
    print(f"Routing decision: {route_decision} (Reason: {response_json.get('reasoning', 'N/A')})")

    if route_decision == "graph_db":
        return {"route": "neo4j"}
    elif route_decision == "vector_db":
        return {"route": "vector"}
    else:
        return {"route": "general"}
        
print("Node 'route_query' defined.")

# Define Synthesis Node
SYNTHESIS_PROMPT_TEMPLATE = """
You are a helpful AI assistant for SLT-MOBITEL. Your job is to answer the user's question based ONLY on the context provided in "Intermediate Steps Context" and the "Chat History".

IMPORTANT RULES:
1. NEVER use your general knowledge to answer questions.
2. If the context is empty, contains an error, or says "No relevant information found", you MUST respond with "I'm sorry, I could not find any specific information about that in our knowledge base."
3. NEVER generate responses about unrelated topics (like dietary fiber when asked about internet fiber products).
4. If Neo4j returned no results for a product query, do NOT generate general knowledge responses.

For questions about SLT products:
- If Neo4j has no results for the specific product category, respond with: "I couldn't find specific information about [product type] in our current product database. You may want to check our official website or contact our customer service for the most up-to-date information."

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
    If Neo4j returns no results for product queries, automatically queries ChromaDB as fallback.
    """
    print("---NODE: generate_response---")
    question = state["question"]
    intermediate_steps = state.get("intermediate_steps", [])
    chat_history = state.get("chat_history", [])
    
    # Check if this is a general question
    original_route = state.get("route", "")
    if original_route == "general":
        # Handle general/greeting questions directly
        if any(greeting in question.lower() for greeting in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
            response = "Hello! I'm your SLT-MOBITEL assistant. How can I help you today? You can ask me about our products, services, or general company information."
        elif any(thanks in question.lower() for thanks in ["thank", "thanks", "thank you"]):
            response = "You're welcome! Is there anything else I can help you with?"
        elif any(ability in question.lower() for ability in ["what can you", "what do you", "how can you", "help"]):
            response = "I can help you with information about SLT-MOBITEL products and services. You can ask about specific product prices, categories, features, or general company information from our website and social media."
        else:
            response = "I'm here to help you with information about SLT-MOBITEL products and services. You can ask about specific products, prices, or general company information."
        
        updated_history = chat_history + [HumanMessage(content=question), AIMessage(content=response)]
        return {"generation": response, "chat_history": updated_history, "intermediate_steps": intermediate_steps}
    
    # Check if Neo4j returned no results for a product query
    neo4j_no_results = False
    for step in intermediate_steps:
        if (step.get("tool") == "neo4j_qa" and 
            ("No result found" in str(step.get("result", "")) or 
             "Error" in str(step.get("result", "")) or
             step.get("no_results", False))):
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
    
    context_str = "\n".join([str(step) for step in intermediate_steps])
    history_str = "\n".join([f"{msg.type.upper()}: {msg.content}" for msg in chat_history])

    final_answer = synthesis_chain.invoke({
        "question": question,
        "intermediate_steps": context_str,
        "chat_history": history_str 
    })
    print(f"Generated final answer: {final_answer}")
    
    updated_history = chat_history + [HumanMessage(content=question), AIMessage(content=final_answer)]
    return {"generation": final_answer, "chat_history": updated_history, "intermediate_steps": intermediate_steps}
print("Node 'generate_response' defined.") 

# Build and Compile the Graph
from langgraph.graph import StateGraph, END

print("Building the LangGraph graph...")
workflow = StateGraph(AgentState)
workflow.add_node("router", route_query)
workflow.add_node("query_neo4j", query_graph_db)
workflow.add_node("query_vector", query_vector_db)
workflow.add_node("generate", generate_response)
workflow.set_entry_point("router")

def decide_next_node(state: AgentState):
    print(f"---DECISION: Based on route '{state['route']}'---")
    if state['route'] == "neo4j":
        return "query_neo4j"
    elif state['route'] == "vector":
        return "query_vector"
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
        "generate": "generate",
        END: END                    
    }
)
workflow.add_edge("query_neo4j", "generate")
workflow.add_edge("query_vector", "generate")
workflow.add_edge("generate", END)

app = workflow.compile()
print("Graph compiled successfully!")
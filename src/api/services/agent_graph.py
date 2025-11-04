import os
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
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

# UPDATED query_graph_db Node 
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
You are an expert router agent. Your task is to determine the best data source to query based on the user's question.
You have two options:
1.  'graph_db': Use this for questions about specific product details, prices, categories, features, counts, or relationships. This includes any questions asking for a list of products, product options, or specific product attributes.
    Examples: "What's the price of X?", "How many Y products are there?", "What category is Z in?", "What router options do I have?", "Show me your security cameras."
2.  'vector_db': Use this for questions requiring semantic search over general company information, website content, social media posts, customer feedback, or open-ended comparisons not directly based on structured product attributes.
    Examples: "What are recent comments about our service?", "Summarize our latest blog post.", "Tell me about the company's mission.", "What's the latest news on LinkedIn?"

Based on the following question, which data source should be queried?
Return ONLY 'graph_db' or 'vector_db' as your answer.

Question: {question}
"""
router_prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT_TEMPLATE)
router_chain = router_prompt | llm | StrOutputParser()
print("Router chain created.")

def route_query(state: AgentState) -> AgentState:
    """
    Determines whether to query the graph database or the vector database.
    """
    print("---NODE: route_query---")
    question = state["question"]
    route_decision = router_chain.invoke({"question": question})
    print(f"Routing decision: {route_decision}")

    if "graph_db" in route_decision.lower():
        return {"route": "neo4j"}
    elif "vector_db" in route_decision.lower():
        return {"route": "vector"}
    else:
        print("Router fallback: defaulting to vector_db")
        return {"route": "vector"}
print("Node 'route_query' defined.")

# Define Synthesis Node 
SYNTHESIS_PROMPT_TEMPLATE = """
You are a helpful AI assistant answering questions based on retrieved information.
Given the chat history and the latest retrieved context (intermediate steps), formulate a final answer to the user's question.
Make the answer conversational.
If the context contains an error message or indicates that the information could not be found, state that clearly.
Do not make up information.
If the context includes a price, format it as "Rs. [price]" (e.g., Rs. 11,410.00).

Chat History:
{chat_history}

Intermediate Steps Context (if any):
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
    """
    print("---NODE: generate_response---")
    question = state["question"]
    intermediate_steps = state["intermediate_steps"]
    chat_history = state.get("chat_history", [])

    context_str = "\n".join([str(step) for step in intermediate_steps])
    history_str = "\n".join([f"{msg.type.upper()}: {msg.content}" for msg in chat_history])

    final_answer = synthesis_chain.invoke({
        "question": question,
        "intermediate_steps": context_str,
        "chat_history": history_str 
    })
    print(f"Generated final answer: {final_answer}")
    
    updated_history = chat_history + [HumanMessage(content=question), AIMessage(content=final_answer)]
    return {"generation": final_answer, "chat_history": updated_history}
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
    else:
        print("Conditional edge fallback: ending.")
        return END

workflow.add_conditional_edges(
    "router",     
    decide_next_node,   
    {
        "query_neo4j": "query_neo4j", 
        "query_vector": "query_vector",
        END: END                    
    }
)
workflow.add_edge("query_neo4j", "generate")
workflow.add_edge("query_vector", "generate")
workflow.add_edge("generate", END)

app = workflow.compile()
print("Graph compiled successfully!")

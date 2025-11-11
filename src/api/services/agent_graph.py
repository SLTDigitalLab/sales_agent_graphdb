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
    question: str             # This will ALWAYS hold the original user question
    chat_history: List[BaseMessage] 
    generation: str 
    intermediate_steps: list 
    route: str
    rephrased_question: str   # This will hold the rephrased question

print("Initial setup complete. AgentState defined.")

# Rephrasing Node
REPHRASE_PROMPT_TEMPLATE = """
You are an expert at rephrasing questions. Your goal is to rewrite the "User's Latest Question" into a complete, standalone question.
Use the "Chat History" to understand the context and resolve ambiguous references like "it", "that", "those", or generic nouns.

**Example 1:**
Chat History:
USER: What security cameras do you have?
AI: We offer the PROLINK DS-3103 Dual Band Outdoor Security Camera.
User's Latest Question: How much is it?
Rephrased Question: What is the price of the PROLINK DS-3103 Dual Band Outdoor Security Camera?

**Example 2:**
Chat History:
(empty)
User's Latest Question: How much is the Tenda MX3?
Rephrased Question: What is the price of Tenda MX3?

**Do not answer the question.** Only output the rephrased question.

Chat History:
{chat_history}

User's Latest Question: {question}

Rephrased Question:
"""
rephrase_prompt = ChatPromptTemplate.from_template(REPHRASE_PROMPT_TEMPLATE)
rephrase_chain = rephrase_prompt | llm | StrOutputParser()
print("Rephrasing chain created.")

def rephrase_question(state: AgentState) -> AgentState:
    """
    Rephrases the user's question to be standalone using chat history.
    """
    print("---NODE: rephrase_question---")
    question = state["question"]
    chat_history = state.get("chat_history", [])
    
    if not chat_history:
        print("No history, skipping rephrase.")
        # The original question is the standalone question
        return {"rephrased_question": question} 

    history_str = "\n".join([f"{msg.type.upper()}: {msg.content}" for msg in chat_history])
    
    rephrased_question = rephrase_chain.invoke({
        "question": question,
        "chat_history": history_str
    })
    
    print(f"Original question: {question}")
    print(f"Rephrased question: {rephrased_question}")
    # Store the new question in 'rephrased_question'
    return {"rephrased_question": rephrased_question}

print("Node 'rephrase_question' defined.")


# Define Nodes 

# query_graph_db Node
def query_graph_db(state: AgentState) -> AgentState:
    """
    Queries the Neo4j SERVICE API based on the *rephrased* question.
    """
    print("---NODE: query_graph_db (calling API)---")
    # Use the rephrased question for the query
    question = state["rephrased_question"] 
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
    Queries the vector database (Chroma DB) SERVICE API based on the *rephrased* question.
    """
    print("---NODE: query_vector_db (calling API)---")
    # Use the rephrased question for the query
    question = state["rephrased_question"] 
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
   - "What's the price of the PROLINK DS-3103 Dual Band Outdoor Security Camera?"
   - "How many Y products are there?"
   - "What router options do I have?"
   - "Show me your security cameras."

2. 'vector_db': Use this for general, open-ended, or semantic questions.
   This includes questions about company information, website content, social media posts, customer feedback, or comparisons not based on structured attributes.
   Examples:
   - "What are recent comments about our service?"
   - "Summarize our latest blog post."
   - "Tell me about the company's mission."

3. 'greeting': Use this for simple greetings, pleasantries, or conversational fillers.
   Examples:
   - "Hello"
   - "Hi"
   - "Thank you"

Based on the following question, which data source should be queried?
Return ONLY 'graph_db', 'vector_db', or 'greeting' as your answer.

Question: {question}
"""
router_prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT_TEMPLATE)
router_chain = router_prompt | llm | JsonOutputParser()
print("Router chain created (JSON Output).")

def route_query(state: AgentState) -> AgentState:
    """
    Determines whether to query the graph, vector db, or just respond.
    """
    print("---NODE: route_query---")
    # Use the rephrased question for routing
    question = state["rephrased_question"] 

    response_json = router_chain.invoke({"question": question})
    route_decision = response_json.get("route", "vector_db")
    
    print(f"Routing decision: {route_decision} (Reason: {response_json.get('reasoning', 'N/A')})")

    if route_decision == "graph_db":
        return {"route": "neo4j"}
    elif route_decision == "greeting":
        return {"route": "greeting"}
    else:
        return {"route": "vector"}
        
print("Node 'route_query' defined.")

# Define Synthesis Node
SYNTHESIS_PROMPT_TEMPLATE = """
You are a helpful and conversational AI assistant. Your job is to answer the user's question based on the context provided in "Intermediate Steps Context".
This context is your only source of truth. Do not use any outside knowledge.

Follow these rules:
1.  **Analyze the "Intermediate Steps Context".**
2.  **If the context *directly* answers the question:** Synthesize a clear and conversational answer.
3.  **If the context is *related* but not a direct answer:** You MUST summarize what you found and present it to the user. For example, if the user asks "How do I get a fiber connection?" and the context is about a "Fiber Connection giveaway", you should say: "I don't have specific steps on how to get a connection, but I found a recent post about a 100GB Fibre Connection giveaway for new customers..."
4.  **If the context is empty, contains an error, or says "No relevant information found":**
    * First, check the "User's Latest Question". If it is a simple greeting or pleasantry (like "Hello", "Hi", "Thanks"), respond with a natural, friendly greeting (e.g., "Hello! How can I help you today?", "You're welcome!").
    * Otherwise (if it was a real question), you MUST respond with "I'm sorry, I could not find any specific information about that."
5.  **Do not make up information.**
6.  If the context includes a price, format it as "Rs. [price]" (e.g., Rs. 11,410.00).

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
    original_question = state["question"] # The *original* user question
    rephrased_question = state["rephrased_question"] # The standalone question
    intermediate_steps = state.get("intermediate_steps", []) 
    chat_history = state.get("chat_history", [])

    context_str = "\n".join([str(step) for step in intermediate_steps])
    history_str = "\n".join([f"{msg.type.upper()}: {msg.content}" for msg in chat_history])

    # Use the rephrased question to get the answer
    final_answer = synthesis_chain.invoke({
        "question": rephrased_question, 
        "intermediate_steps": context_str,
        "chat_history": history_str 
    })
    print(f"Generated final answer: {final_answer}")
    
    # Save the *original* question and the final answer to history
    updated_history = chat_history + [HumanMessage(content=original_question), AIMessage(content=final_answer)]
    return {"generation": final_answer, "chat_history": updated_history}

print("Node 'generate_response' defined.") 

# Build and Compile the Graph
from langgraph.graph import StateGraph, END

print("Building the LangGraph graph...")
workflow = StateGraph(AgentState)
workflow.add_node("rephrase_question", rephrase_question) # New node
workflow.add_node("router", route_query)
workflow.add_node("query_neo4j", query_graph_db)
workflow.add_node("query_vector", query_vector_db)
workflow.add_node("generate", generate_response)

# Set the new entry point
workflow.set_entry_point("rephrase_question") 

# Add edge from rephraser to router
workflow.add_edge("rephrase_question", "router")

# Define Conditional Edges (from router)
def decide_next_node(state: AgentState):
    print(f"---DECISION: Based on route '{state['route']}'---")
    if state['route'] == "neo4j":
        return "query_neo4j"
    elif state['route'] == "vector":
        return "query_vector"
    elif state['route'] == "greeting":
        return "generate" # Skip tools, go straight to synthesis
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

# Add remaining edges
workflow.add_edge("query_neo4j", "generate")
workflow.add_edge("query_vector", "generate")
workflow.add_edge("generate", END)

app = workflow.compile()
print("Graph compiled successfully!")
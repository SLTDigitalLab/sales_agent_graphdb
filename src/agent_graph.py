import os
from typing import TypedDict, Annotated, List, Union
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

graph = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USER,
    password=NEO4J_PASSWORD
)

try:
    graph.refresh_schema()
    print("Neo4j schema refreshed.")
except Exception as e:
    print(f"Error refreshing Neo4j schema: {e}")
    # if want to exit or continue without schema
    # exit()


# Define Agent State
class AgentState(TypedDict):
    question: str                
    chat_history: List[BaseMessage] 
    generation: str               
    intermediate_steps: list      
    route: str                    

print("Initial setup complete. AgentState defined.")

# Neo4j QA chain definition
QA_TEMPLATE_TEXT = """
You are an assistant that helps to form nice and human-readable answers.
The information part contains the provided information that you must use to construct an answer.
The provided information is authoritative, you must never doubt it or try to use your internal knowledge to correct it.
Make the answer sound as a response to the question.
If the provided information is empty, say that you don't know the answer.

**IMPORTANT:** All prices are in Sri Lankan Rupees (Rs.). When you state a price, format it as "Rs. [price]".
For example: Rs. 11,410.00

Information:
{context}

Question: {question}
Helpful Answer:
"""
QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template=QA_TEMPLATE_TEXT
)

neo4j_qa_chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    verbose=True, # Set to False for cleaner production output
    allow_dangerous_requests=True,
    qa_prompt=QA_PROMPT
)

print("Neo4j QA Chain created.")


#Define Nodes

def query_graph_db(state: AgentState) -> AgentState:
    """
    Queries the Neo4j graph database based on the question.
    """
    print("---NODE: query_graph_db---")
    question = state["question"]
    intermediate_steps = state.get("intermediate_steps", []) 

    try:
        result = neo4j_qa_chain.invoke({"query": question})
        intermediate_steps.append({"tool": "neo4j_qa", "result": result['result']})
    except Exception as e:
        print(f"Error querying Neo4j: {e}")
        intermediate_steps.append({"tool": "neo4j_qa", "error": str(e)})

    return {"intermediate_steps": intermediate_steps}

print("Node 'query_graph_db' defined.")

# Placeholder for Vector DB Node
def query_vector_db(state: AgentState) -> AgentState:
    """
    Placeholder node for querying the vector database (Chroma DB).
    """
    print("---NODE: query_vector_db---")
    question = state["question"]
    intermediate_steps = state.get("intermediate_steps", [])

    # Placeholder message
    intermediate_steps.append({"tool": "vector_db", "result": "Vector DB lookup is not implemented yet."})

    return {"intermediate_steps": intermediate_steps}

print("Node 'query_vector_db' defined.")

# Define Router Logic

ROUTER_PROMPT_TEMPLATE = """
You are an expert router agent. Your task is to determine the best data source to query based on the user's question.
You have two options:
1.  'graph_db': Use this for questions about specific product details, prices, categories, features, counts, or relationships between products stored in a structured knowledge graph.
    Examples: "What's the price of X?", "How many Y products are there?", "What category is Z in?"
2.  'vector_db': Use this for questions requiring semantic search over general company information, website content, social media posts, customer feedback, or open-ended comparisons not directly based on structured product attributes.
    Examples: "What are recent comments about our service?", "Summarize our latest blog post.", "Tell me about the company's mission."

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

    # Run the router chain
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
You are an AI assistant tasked with generating a final answer based on retrieved information and the original question.
Use the provided context (intermediate steps) to answer the user's question accurately.
If the context contains an error message or indicates that the information could not be found, state that clearly.
Do not make up information.
If the context includes a price, format it as "Rs. [price]" (e.g., Rs. 11,410.00).

Intermediate Steps Context:
{intermediate_steps}

Original Question: {question}

Final Answer:
"""

synthesis_prompt = ChatPromptTemplate.from_template(SYNTHESIS_PROMPT_TEMPLATE)

synthesis_chain = synthesis_prompt | llm | StrOutputParser()

print("Synthesis chain created.")

def generate_response(state: AgentState) -> AgentState:
    """
    Generates the final response to the user based on intermediate steps.
    """
    print("---NODE: generate_response---")
    question = state["question"]
    intermediate_steps = state["intermediate_steps"]

    context_str = "\n".join([str(step) for step in intermediate_steps])

    # Run the synthesis chain
    final_answer = synthesis_chain.invoke({
        "question": question,
        "intermediate_steps": context_str
    })

    print(f"Generated final answer: {final_answer}")

    return {"generation": final_answer}

print("Node 'generate_response' defined.")

from langgraph.graph import StateGraph, END

# Build the Graph 

print("Building the LangGraph graph...")

workflow = StateGraph(AgentState)

# Add the nodes to the graph
workflow.add_node("router", route_query)
workflow.add_node("query_neo4j", query_graph_db)
workflow.add_node("query_vector", query_vector_db)
workflow.add_node("generate", generate_response)

workflow.set_entry_point("router")

# Define Conditional Edges
def decide_next_node(state: AgentState):
    print(f"---DECISION: Based on route '{state['route']}'---")
    if state['route'] == "neo4j":
        return "query_neo4j"
    elif state['route'] == "vector":
        return "query_vector"
    else:
        print("Conditional edge fallback: ending.")
        return END

# Add the conditional edge from the router
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

# Compile the Graph
app = workflow.compile()

print("Graph compiled successfully!")

# Example Usage 
if __name__ == "__main__":
    print("\n--- Running Graph Example ---")
    inputs = {"question": "What is the price of the eMark GM4 Mini UPS?"}
    
    for output in app.stream(inputs, stream_mode="values"):
        step_name = list(output.keys())[0]
        print(f"\nOutput from step '{step_name}':")
        print(output[step_name])
        print("-" * 30)

    print("\n--- Example Finished ---")

    # Example for the vector store path using the placeholder
    print("\n--- Running Graph Example (Vector Path) ---")
    inputs_vector = {"question": "Tell me about the company mission"}
    for output in app.stream(inputs_vector, stream_mode="values"):
        step_name = list(output.keys())[0]
        print(f"\nOutput from step '{step_name}':")
        print(output[step_name])
        print("-" * 30)
    print("\n--- Example Finished ---")

    # Test Examples
    print("\n--- Running Graph Example ---")
    inputs_vector = {"question": "Which products are in the Security Cameras category?"}
    for output in app.stream(inputs_vector, stream_mode="values"):
        step_name = list(output.keys())[0]
        print(f"\nOutput from step '{step_name}':")
        print(output[step_name])
        print("-" * 30)
    print("\n--- Example Finished ---")

    inputs_vector = {"question": "Tell me about wifi routers"}
    for output in app.stream(inputs_vector, stream_mode="values"):
        step_name = list(output.keys())[0]
        print(f"\nOutput from step '{step_name}':")
        print(output[step_name])
        print("-" * 30)
    print("\n--- Example Finished ---")
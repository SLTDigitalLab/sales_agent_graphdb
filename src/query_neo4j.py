import os
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
from langchain_openai import ChatOpenAI
from langchain_neo4j import GraphCypherQAChain
from langchain_core.prompts import PromptTemplate

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file.")

print("All credentials loaded successfully.")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

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

try:
    print("Connecting to Neo4j...")
    graph = Neo4jGraph(
        url=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASSWORD
    )
    
    graph.refresh_schema()
    print("Graph schema refreshed.")

    print("Creating GraphCypherQAChain...")
    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        verbose=True,
        allow_dangerous_requests=True,
        qa_prompt=QA_PROMPT
    )
    print("Chain created successfully.")

    # --- Questions ---
    print("\n--- Asking question ---")
    question = "What is the price of the eMark GM4 Mini UPS?"
    
    response = chain.invoke({"query": question})
    
    print("\n--- Response ---")
    print(f"Question: {question}")
    print(f"Answer: {response['result']}")

    print("\n--- Asking another question ---")
    question_2 = "How many products are in the Wi-Fi Devices category?"
    
    response_2 = chain.invoke({"query": question_2})
    
    print("\n--- Response ---")
    print(f"Question: {question_2}")
    print(f"Answer: {response_2['result']}")


except Exception as e:
    print(f"An error occurred: {e}")
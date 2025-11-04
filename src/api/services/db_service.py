from typing import List, Dict, Any
import asyncio
from langchain_core.documents import Document

# ⬅️ IMPORT YOUR RETRIEVER FROM THE PARENT DIRECTORY 
# Assuming agent_graph.py is in the project root
try:
    from agent_graph import retriever 
except ImportError:
    print("WARNING: Could not import retriever from agent_graph.py.")
    retriever = None

# Defining the structure of the data to be returned
class DocumentResult(BaseModel):
    page_content: str
    metadata: Dict[str, Any]


async def get_raw_chunks(query: str, k: int = 3) -> List[DocumentResult]:
    """
    Executes the synchronous retrieval method in a separate thread.
    """
    if not retriever:
        print("Retriever not available.")
        return []
        
    # Safely run the synchronous retriever call
    docs: List[Document] = await asyncio.to_thread(
        retriever.get_relevant_documents, 
        query, 
        k=k
    )

    results = []
    for doc in docs:
        results.append(
            DocumentResult(
                page_content=doc.page_content,
                metadata=doc.metadata
            )
        )
    
    return results
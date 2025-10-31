import os
import json
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions

load_dotenv()


class ChromaVectorStore:
    def __init__(self, persist_directory="chroma_data"):
        script_dir = os.path.dirname(__file__)
        project_root = os.path.join(script_dir, '..')
        self.persist_directory_path = os.path.join(project_root, persist_directory)
        
        os.makedirs(self.persist_directory_path, exist_ok=True)

        self.client = chromadb.PersistentClient(path=self.persist_directory_path) 
        
        self.embedding_func = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"), 
            model_name="text-embedding-3-small"
        )

        self.collection = self.client.get_or_create_collection(
            name="enterprise_data",
            embedding_function=self.embedding_func
        )

    def load_json_data(self, file_path):
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {file_path}. File might be empty or corrupt.")
            return []

    def ingest_data(self, data_list, source):
        if not data_list:
            print(f"No data found for {source}. Skipping.")
            return

        print(f"Preparing {len(data_list)} {source} entries for ChromaDB...")

        documents_batch = []
        metadatas_batch = []
        ids_batch = []

        for i, entry in enumerate(data_list):
            if isinstance(entry, dict):
                text = entry.get("post_text") or entry.get("text") or entry.get("title") or entry.get("description")
            else:
                text = str(entry)
            
            if not text or text == "Error scraping post details":
                print(f"Skipping entry {i} from {source} due to missing or error text.")
                continue

            documents_batch.append(text)
            metadatas_batch.append({"source": source})
            ids_batch.append(f"{source}_{i}")

        if documents_batch:
            print(f"Ingesting {len(documents_batch)} documents from {source} into ChromaDB...")
            self.collection.add(
                ids=ids_batch,
                documents=documents_batch,
                metadatas=metadatas_batch
            )
            print(f"{source} data successfully stored in ChromaDB!")
        else:
            print(f"No valid documents found to ingest for {source}.")

    def query_similar(self, query_text, n_results=3):
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results

if __name__ == "__main__":
    store = ChromaVectorStore(persist_directory="chroma_data") 

    script_dir = os.path.dirname(__file__)
    data_dir = os.path.join(script_dir, '..', 'data')

    # Load Website Data
    website_json_path = os.path.join(data_dir, "website_data.json")
    print(f"Loading website data from: {website_json_path}")
    website_json = store.load_json_data(website_json_path)
    
    # Load LinkedIn Data
    linkedin_json_path = os.path.join(data_dir, "linkedin_data.json")
    print(f"Loading linkedin data from: {linkedin_json_path}")
    linkedin_json = store.load_json_data(linkedin_json_path)
    
    # Extract data from loaded JSONs
    website_data = website_json.get("data", []) if isinstance(website_json, dict) else website_json
    linkedin_data = linkedin_json.get("data", []) if isinstance(linkedin_json, dict) else linkedin_json

    # Ingest data from each source
    store.ingest_data(website_data, "website")
    store.ingest_data(linkedin_data, "linkedin")

    try:
        total_items = store.collection.count()
        print(f"\n--- Ingestion Complete ---")
        print(f"Total items in ChromaDB collection 'enterprise_data': {total_items}")
        print(f"Database data is saved in the '{store.persist_directory_path}' folder.")
    except Exception as e:
        print(f"Error counting items in collection: {e}")


    # Test query
    print("\nTesting semantic search...")
    query = "broadband internet speed"
    try:
        results = store.query_similar(query)
        print(f"Query results for '{query}':")
        if results and results.get('documents'):
             for i, doc in enumerate(results['documents'][0]):
                 print(f"  Result {i+1}: {doc[:100]}...")
                 if results.get('metadatas') and results['metadatas'][0][i]:
                     print(f"    Source: {results['metadatas'][0][i].get('source')}")
                 if results.get('distances') and results['distances'][0][i] is not None:
                     print(f"    Distance: {results['distances'][0][i]:.4f}")
        else:
            print("  No results found or error in query.")

    except Exception as e:
        print(f"Error during test query: {e}")
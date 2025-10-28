import os
import json
from dotenv import load_dotenv
from chromadb import PersistentClient  # <--- CHANGE: Imported PersistentClient
import chromadb # <--- CHANGE: Imported chromadb
from chromadb.utils import embedding_functions

load_dotenv()


class ChromaVectorStore:
    def __init__(self, persist_directory="chroma_data"):
        os.makedirs(persist_directory, exist_ok=True)

        # <--- CHANGE: Switched to PersistentClient to save data to disk
        self.client = chromadb.PersistentClient(path=persist_directory) 
        
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

        # <--- CHANGE: Create lists for batch ingestion
        documents_batch = []
        metadatas_batch = []
        ids_batch = []

        for i, entry in enumerate(data_list):
            if isinstance(entry, dict):
                text = entry.get("text") or entry.get("title") or entry.get("description")
            else:
                text = str(entry)
            
            if not text:
                print(f"Skipping entry {i} from {source} due to missing text.")
                continue

            # <--- CHANGE: Add to batch lists instead of calling self.collection.add
            documents_batch.append(text)
            metadatas_batch.append({"source": source})
            ids_batch.append(f"{source}_{i}")

        # <--- CHANGE: Add all documents in one single batch after the loop
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
    # The persist_directory name must match the one in __init__
    store = ChromaVectorStore(persist_directory="chroma_data") 

    website_json = store.load_json_data("../data/website_data.json")
    facebook_json = store.load_json_data("../data/facebook_data.json")
    youtube_json = store.load_json_data("../data/youtube_data.json")

    website_data = website_json.get("data", []) if isinstance(website_json, dict) else website_json
    facebook_data = facebook_json.get("data", []) if isinstance(facebook_json, dict) else facebook_json
    youtube_data = youtube_json.get("data", []) if isinstance(youtube_json, dict) else youtube_json

    store.ingest_data(website_data, "website")
    store.ingest_data(facebook_data, "facebook")
    store.ingest_data(youtube_data, "youtube")

    # <--- CHANGE: Added a final count to confirm persistence
    total_items = store.collection.count()
    print(f"\n--- Ingestion Complete ---")
    print(f"Total items in ChromaDB: {total_items}")
    print("Database is now saved in the 'chroma_data' folder.")

    print("\nTesting semantic search...")
    query = "broadband internet speed"
    results = store.query_similar(query)
    print("Query results:")
    print(results)
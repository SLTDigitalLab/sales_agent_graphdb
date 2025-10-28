import os
import json
from dotenv import load_dotenv
from chromadb import Client
from chromadb.utils import embedding_functions

load_dotenv()


class ChromaVectorStore:
    def __init__(self, persist_directory="chroma_data"):
        os.makedirs(persist_directory, exist_ok=True)

        self.client = Client()
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

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def ingest_data(self, data_list, source):
        if not data_list:
            print(f"No data found for {source}. Skipping.")
            return

        print(f"Ingesting {len(data_list)} {source} entries into ChromaDB...")

        for i, entry in enumerate(data_list):
            if isinstance(entry, dict):
                text = entry.get("text") or entry.get("title") or entry.get("description")
            else:
                text=str(entry)
            if not text:
                continue

            self.collection.add(
                ids=[f"{source}_{i}"],
                documents=[text],
                metadatas=[{"source": source}]
            )

        print(f"{source} data successfully stored in ChromaDB!")

    def query_similar(self, query_text, n_results=3):
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results


if __name__ == "__main__":
    store = ChromaVectorStore()

    website_json = store.load_json_data("data/website_data.json")
    facebook_json = store.load_json_data("data/facebook_data.json")
    youtube_json = store.load_json_data("data/youtube_data.json")

    website_data = website_json.get("data", []) if isinstance(website_json, dict) else website_json
    facebook_data = facebook_json.get("data", []) if isinstance(facebook_json, dict) else facebook_json
    youtube_data = youtube_json.get("data", []) if isinstance(youtube_json, dict) else youtube_json

    store.ingest_data(website_data, "website")
    store.ingest_data(facebook_data, "facebook")
    store.ingest_data(youtube_data, "youtube")

    print("\n Testing semantic search...")
    query = "broadband internet speed"
    results = store.query_similar(query)
    print(results)

   
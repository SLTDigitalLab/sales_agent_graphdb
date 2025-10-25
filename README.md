# AI-Enterprise-Agent

AI-powered enterprise assistant for knowledge and product intelligence. It combines a Neo4j graph database for structured product data with a Chroma DB vector store for unstructured web content, all orchestrated by a LangGraph agent.

---

## Setup and Installation

Follow these steps to set up your local development environment.

### 1. Prerequisites

* **Python:** This project requires **Python 3.10 or newer**. 

* **Neo4j Desktop:** A running Neo4j database instance is required for the knowledge graph.

### 2. Environment Setup

1.  **Clone the repository**

2.  **Create and activate a virtual environment:**
    ```bash
    # Create the environment
    python -m venv venv

    # Activate on macOS/Linux
    source venv/bin/activate

    # Activate on Windows
    .\venv\Scripts\activate
    ```

3.  **Install all required packages:**
    Use the `requirements.txt` file to install the exact versions of all dependencies for the project.
    ```bash
    pip install -r requirements.txt
    ```

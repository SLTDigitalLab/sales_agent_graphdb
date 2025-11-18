# AI-Enterprise-Agent

AI-powered enterprise assistant for knowledge and product intelligence. It combines a Neo4j graph database for structured product data with a Chroma DB vector store for unstructured web content, all orchestrated by a LangGraph agent.

---

## Setup and Installation

Follow these steps to set up your local development environment.

### 1. Prerequisites

* **Python:** Requires **Python 3.10 or newer**. 

### 2. Environment Setup

1.  **Clone the repository**

2.  **Create and activate a virtual environment:**
    ```bash
    # Create the environment
    python -m venv venv

    # Activate on macOS/Linux
    source venv/bin/activate

    # Activate on Windows
    .venv\Scripts\activate
    ```

3.  **Install all required packages:**
    Use the `requirements.txt` file to install the exact versions of all dependencies for the project.
    ```bash
    pip install -r requirements.txt
    ```
## Execution 

Once the environment is set up, follow these steps to run the application:

4.  **Run the backend server:**
    Start the main application backend, which houses the LangGraph agent and API services.
    ```bash
    uvicorn src.main:api --reload --port 8000
    ```
    The backend API and Swagger UI will be available at `http://localhost:8000`.

5.  **Access the Admin Dashboard:**
    Acess the Admin Dashboard to controll scraping and data ingection.
    
    The Admin Dashboard will be available at `http://localhost:8000/admin-ui/`.
    
6.  **Run the chat application:**
    Navigate to the `frontend` directory and start the development server.
    ```bash
    cd frontend
    npm install 
    npm run dev
    ```
    The frontend will typically be available at **http://localhost:5173**.

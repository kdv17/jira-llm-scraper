# Jira LLM Corpus Scraper

This project contains a Python-based data pipeline for scraping public issue data from Apache's Jira instance and transforming it into a structured JSONL corpus suitable for training Large Language Models (LLMs).

This solution is designed to be **fault-tolerant**, **resumable**, and **efficient**. It bypasses fragile HTML scraping by using the official Jira REST API, which provides structured JSON data directly.

##  Architecture

The system is built with a modular Python architecture:

- **`main.py`**: The main entry point. It iterates through projects and manages the overall pipeline.
- **`api.py`**: A dedicated API client class (`JiraAPI`) that handles all communication with the Jira REST API.
- **`processor.py`**: The data transformation engine. It uses Pydantic models (`LLMTrainingSample`) to validate raw data and convert it into the target schema. This is where text is cleaned and derived tasks are generated.
- **`state_manager.py`**: A simple file-based state manager that tracks the pagination index (`startAt`) for each project, allowing the scraper to be stopped and resumed without data loss.
- **`config.py`**: A simple configuration file to list the target Jira projects (e.g., `['SPARK', 'HADOOP', 'KAFKA']`).

### Core Technologies

- **Python 3.10+**
- **Requests**: For all HTTP communication.
- **Tenacity**: For robust, exponential-backoff retries. This is the primary mechanism for handling network failures, timeouts, HTTP 429 (Rate Limits), and 5xx (Server Errors).
- **Pydantic**: For data validation, cleaning, and transformation. This ensures a clean, consistent output schema and gracefully handles missing or malformed data from the API.
- **Jsonlines**: For efficiently writing the output to a `.jsonl` file, which is a standard format for LLM training.

## Setup and Installation

1.  **Create a virtual environment:**

    ```
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install dependencies:**

    ```
    pip install -r requirements.txt
    ```

3.  **Configure projects:**
    
    ```python
    # config.py
    PROJECTS = ['SPARK', 'HADOOP', 'KAFKA']
    ```

4.  **Run the scraper:**
    ```
    python main.py
    ```


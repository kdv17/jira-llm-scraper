# Jira LLM Corpus Scraper

This project contains a Python-based data pipeline for scraping public issue data from Apache's Jira instance and transforming it into a structured JSONL corpus suitable for training Large Language Models (LLMs).

This solution is designed to be **fault-tolerant**, **resumable**, and **efficient**. It bypasses fragile HTML scraping by using the official Jira REST API, which provides structured JSON data directly.

## 🚀 Architecture

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

## ⚙️ Setup and Installation

1.  **Clone the repository:**

    ```bash
    git clone [https://github.com/Naman-Bhalla/jira-llm-scraper.git](https://github.com/Naman-Bhalla/jira-llm-scraper.git)
    # (Or your own fork/repo location)
    cd jira-llm-scraper
    ```

2.  **Create a virtual environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure projects:**
    Edit `config.py` to list the projects you want to scrape.

    ```python
    # config.py
    PROJECTS = ['SPARK', 'HADOOP', 'KAFKA']
    ```

5.  **Run the scraper:**
    ```bash
    python main.py
    ```

The scraper will print its progress and create a `{project_key}_corpus.jsonl` file for each project. It will also create `{project_key}_state.json` files to track its progress. You can stop the script (`Ctrl+C`) and restart it, and it will resume from the last completed batch.

## 🛡️ Fault-Tolerance & Edge Cases Handled

This system was designed to handle real-world data and network instability.

- **HTTP 429 (Rate Limit) & 5xx (Server Errors)**: Handled automatically by the `@retry` decorator in `api.py`. It uses exponential backoff (up to 7 attempts) to wait and try again without overwhelming the server.
- **Interruption / Resumption**: The `state_manager.py` saves the `startAt` pagination index after _every_ successful batch. If the script is stopped, it reads this file on restart and continues exactly where it left off, preventing duplicate work.
- **Malformed/Missing Data**: Pydantic models in `processor.py` solve this. If an issue is missing a field (e.g., `assignee` is `null`), the `Optional` type handles it, and the field is set to `None`. If a _required_ field were missing, Pydantic would raise a `ValidationError`, which is caught, logged, and the specific issue is skipped, preventing one bad record from crashing the entire pipeline.
- **Data Transformation**: Jira's description and comment fields contain wiki markup. A regex-based cleaner (`clean_jira_text`) is used to strip this markup and provide plain text suitable for an LLM.

## 💡 Optimizations & Future Improvements

### Optimizations Implemented

- **API vs. HTML**: The single biggest optimization is using the REST API, which is orders of magnitude faster and more reliable than HTML scraping.
- **JQL Sorting**: We use `ORDER BY created ASC` in our JQL query. This ensures a stable, consistent order for pagination, which is critical for the resumption logic to work correctly.
- **Selective Fields**: The API call explicitly requests _only_ the necessary fields (`summary`, `description`, `comment`, etc.) using the `fields` parameter. This significantly reduces payload size and speeds up API response times.

### Potential Future Improvements

- **Async/Concurrency**: For even greater speed, the `requests` library could be replaced with `httpx` and `asyncio`. We could run all project scrapers in parallel or use an `asyncio.Semaphore` to fetch multiple batches concurrently for a single project.
- **Advanced Text Cleaning**: The current regex cleaner is basic. A more advanced solution would use a dedicated library to parse Jira's Atlassian Document Format (ADF) for a more structured text extraction.
- **Distributed State**: For a very large-scale system, the file-based state manager could be replaced with a Redis or a small database to handle state for hundreds of projects.
- **Better Derived Tasks**: The derived tasks are simple Q&A. This could be expanded to include code generation (e.g., "Write a test case for this bug report"), more complex classification (e.g., sentiment analysis of comments), or instruction-following from the description.

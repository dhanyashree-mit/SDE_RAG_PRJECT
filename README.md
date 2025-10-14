# RAG Service for Website Q&A

This repository contains a self-contained RAG service that can crawl, index, and answer questions about a given website.

## Setup & Run

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/dhanyashree-mit/SDE_RAG_PRJECT
    cd <your-repo-folder>
    ```

2.  **Install dependencies and run:**
    ```bash
    pip install -r requirements.txt
    python app.py
    ```
The application will be available at `http://127.0.0.1:7860`. The required LLM model will be downloaded automatically on first run.

## Evaluate

1.  **Crawl:** Open the UI, enter a URL (e.g., `http://books.toscrape.com`), and click "Start Crawl".
2.  **Index:** Go to the "Index" tab and click "Index Crawled Content".
3.  **Ask:** Go to the "Ask" tab and ask a question based on the site's content (e.g., "what are the category of books?").

## Architecture, Design, and Tradeoffs

* **Architecture: Async Crawler**: The system uses Python's `asyncio` with `aiohttp` for a lightweight and fast asynchronous web crawler.
* **Architecture: Content Extraction**: `BeautifulSoup` parses the HTML. It intelligently removes common boilerplate tags (`<nav>`, `<footer>`, etc.) to isolate high-quality text for indexing.
* **Architecture: Vector Indexing**: Text is chunked by word count and vectorized using the `paraphrase-MiniLM-L3-v2` model. Vectors are stored in a local `ChromaDB` database for efficient retrieval.
* **Architecture: Grounded Generation**: A local `Mistral-7B` model generates answers. It is constrained by a specific prompt to *only* use the retrieved text, preventing hallucination.
* **Tradeoff: Crawler Choice**: Used `aiohttp` for a very fast crawler that is perfect for static HTML sites. This is more efficient than a full browser-based solution but would not work on sites that require JavaScript to load their content.
* **Tradeoff: Local Models**: The project exclusively uses local, open-source models (SentenceTransformer, Mistral-7B). This makes the service free to run with no API keys, at the cost of potentially lower accuracy than large, cloud-based models like GPT-4.
* **Tradeoff: UI vs. API**: A `Gradio` UI was built for ease of use and rapid demonstration. This is faster to implement than a formal REST API but is less suitable for programmatic integration.
* **Design: Politeness**: The crawler respects `robots.txt` rules and uses a crawl delay and concurrency limits to avoid overwhelming the target server.
* **Design: Safety & Refusals**: The core prompt explicitly instructs the LLM on how to refuse questions ("Not found in crawled content") when the answer is not in the retrieved context, fulfilling the grounding requirement.

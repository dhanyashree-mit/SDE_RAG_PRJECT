# RAG Service for Website Q&A

This repository contains a self-contained RAG service that can crawl, index, and answer questions about a given website.

## Setup & Run

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/dhanyashree-mit/SDE_RAG_PRJECT
    cd SDE_RAG_PRJECT
    
    ```

2.  **Install dependencies and run:**
    ```bash
    pip install -r requirements.txt
    python app.py
    ```
The application will be available at `http://127.0.0.1:7860`. The required LLM model will be downloaded automatically on first run.

## Evaluation Samples

[cite_start]Here are the required example requests and responses for the `crawl`, `index`, and `ask` functions.

### 1. Crawl Example

* **Action (Request):** In the "Crawl" tab, I entered the Start URL `http://books.toscrape.com` and clicked the "Start Crawl" button.
* **Response:**
    ```json
    {
      "page_count": 61,
      "skipped_count": 0,
      "urls": [
        "[http://books.toscrape.com/](http://books.toscrape.com/)",
        "[http://books.toscrape.com/catalogue/category/books/travel_2/index.html](http://books.toscrape.com/catalogue/category/books/travel_2/index.html)",
        "..."
      ]
    }
    ```

### 2. Index Example

* **Action (Request):** After the crawl was complete, I went to the "Index" tab and clicked the "Index Crawled Content" button.
* **Response:**
    ```json
    {
      "vector_count": 62
    }
    ```

### 3. Ask Example (Successful Answer)

[cite_start]This example demonstrates a successful answer with a cited URL and snippet.

* **Action (Request):** In the "Ask" tab, I asked the question: `"what are the category of books?"`
* **Response:**
    ```json
    {
      "answer": "The categories of books mentioned in the context include Fiction, Travel Mystery, Historical Fiction, Sequential Art, Classics, Philosophy, Romance, Womens Fiction, Fiction Childrens, Religion, Nonfiction, Music, Science Fiction, Sports and Games, Add a comment, Fantasy New Adult Young Adult Science Poetry Paranormal Art Psychology Autobiography Parenting Adult Fiction Humor Horror History Food and Drink Christian Fiction Business Biography Thriller Contemporary Spirituality Academic Self Help Historical Christian Suspense Short",
      "sources": [
        {
  "sources": [
    {
      "url": "http://books.toscrape.com/catalogue/soumission_998/index.html",
      "snippet": "Soumission | Books to Scrape - Sandbox Home Books Fiction Soumission Soumission £50.10 In stock (20 available) Warning! This is a demo website for web scraping purposes. Prices and ratings here were r"
    },
    {
      "url": "http://books.toscrape.com/catalogue/category/books/default_15/index.html",
      "snippet": "Default | Books to Scrape - Sandbox Home Books Default Books Travel Mystery Historical Fiction Sequential Art Classics Philosophy Romance Womens Fiction Fiction Childrens Religion Nonfiction Music Def"
    },
    {
      "url": "http://books.toscrape.com/catalogue/the-coming-woman-a-novel-based-on-the-life-of-the-infamous-feminist-victoria-woodhull_993/index.html",
      "snippet": "The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull | Books to Scrape - Sandbox Home Books Default The Coming Woman: A Novel Based on the Life of the Infamous Femin"
    }
  ],
  "timings": {
    "retrieval_s": 0.09,
    "generation_s": 374.629,
    "total_s": 374.719
  }
}
      ]
    }
    ```

### 4. Ask Example (Refusal)

[cite_start]This example demonstrates a refusal when the information is not in the crawled content. [cite_start]The response correctly includes the closest retrieved snippets as evidence[cite: 28].

* **Action (Request):** In the "Ask" tab, I asked a question that cannot be answered from the site's content: `"What is the publisher of the book 'It's Only the Himalayas'?"`
* **Response:**
    ```json
    {
      "answer": "Not found in crawled content.",
      "sources": [
        {
          "url": "[http://books.toscrape.com/catalogue/its-only-the-himalayas_981/index.html](http://books.toscrape.com/catalogue/its-only-the-himalayas_981/index.html)",
          "snippet": "It's Only the Himalayas by S. Bedford ★★★★★ ... Product Information UPC a22124811b2d2b77 Product Type Books"
        }
      ]
    }
    ```

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

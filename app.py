from utils import same_domain, chunk_text_words
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import tldextract
import urllib.robotparser as robotparser
import time
import gradio as gr
from sentence_transformers import SentenceTransformer
import chromadb
from gpt4all import GPT4All
gpt_model = GPT4All("mistral-7b-openorca.Q4_0.gguf")


MAX_PAGES = 50
CRAWL_CONCURRENCY = 20
CRAWL_DELAY = 0.05
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3
EMBEDDING_MODEL = "sentence-transformers/paraphrase-MiniLM-L3-v2"


pages = {}
skipped_robots = []

client = chromadb.PersistentClient(path="./db")
collection = client.get_or_create_collection("web_pages")
embedder = SentenceTransformer(EMBEDDING_MODEL)


async def fetch_page(session, url, rp):
    """Fetch page using aiohttp and parse with BeautifulSoup"""
    if not rp.can_fetch("*", url):
        skipped_robots.append(url)
        return None, url, None

    try:
        async with session.get(url, timeout=10) as response:
            if response.status != 200:
                return None, url, None

            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            
            for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "form"]):
                tag.decompose()

           
            main_content = soup.find("main") or soup.find("div", {"id": "content"}) or soup
            text = main_content.get_text(separator=" ", strip=True)
            text = " ".join(text.split())  # normalize whitespace

            return text, url, html

    except Exception:
        return None, url, None


# ---------------------------
# CRAWLER
# ---------------------------
async def crawl_site_async(start_url, second_url=None):
    domain_extract = tldextract.extract(start_url)
    base_url = f"https://{domain_extract.domain}.{domain_extract.suffix}"
    robots_url = urljoin(base_url, "/robots.txt")

    rp = robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except:
        pass

    to_visit = [start_url]
    if second_url and same_domain(start_url, second_url):
        to_visit.append(second_url)
    visited = set()
    pages.clear()
    global skipped_robots
    skipped_robots = []

    connector = aiohttp.TCPConnector(limit_per_host=CRAWL_CONCURRENCY, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        while to_visit and len(pages) < MAX_PAGES:
            batch = []
            while to_visit and len(batch) < CRAWL_CONCURRENCY:
                batch.append(to_visit.pop(0))

            tasks = [fetch_page(session, url, rp) for url in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if not result or isinstance(result, Exception):
                    continue

                content, url, html = result
                if content:
                    pages[url] = content
                    visited.add(url)
                    soup = BeautifulSoup(html, "html.parser")

                    for link_tag in soup.find_all("a", href=True):
                        link = urljoin(url, link_tag["href"])
                        if (
                            same_domain(start_url, link)
                            and link not in visited
                            and link not in to_visit
                            and rp.can_fetch("*", link)
                        ):
                            to_visit.append(link)

            await asyncio.sleep(CRAWL_DELAY)

    return {
        "page_count": len(pages),
        "skipped_count": len(skipped_robots),
        "skipped_robots": skipped_robots,
        "urls": list(pages.keys()),
    }


# ---------------------------
# INDEXING
# ---------------------------
def index_site(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    global collection
    try:
        client.delete_collection("web_pages")
    except:
        pass
    collection = client.get_or_create_collection("web_pages")

    all_chunks, all_ids, all_metas = [], [], []
    for url, content in pages.items():
        chunks = chunk_text_words(content, size=chunk_size, overlap=chunk_overlap)
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_ids.append(f"{url}_{i}")
            all_metas.append({"url": url})

    embeddings = embedder.encode(all_chunks, batch_size=128, show_progress_bar=True).tolist()
    batch_size = 5000
    for start_idx in range(0, len(all_chunks), batch_size):
        end_idx = min(start_idx + batch_size, len(all_chunks))
        collection.add(
            ids=all_ids[start_idx:end_idx],
            metadatas=all_metas[start_idx:end_idx],
            documents=all_chunks[start_idx:end_idx],
            embeddings=embeddings[start_idx:end_idx]
        )
    return {"vector_count": len(all_chunks)}


# ---------------------------
# QUESTION ANSWERING
# ---------------------------

def ask_question_strict(question, top_k=TOP_K):
    import time as t
    timings = {}

    start_retrieval = t.time()
    q_embedding = embedder.encode([question]).tolist()[0]

    try:
        results = collection.query(
            query_embeddings=[q_embedding],
            n_results=top_k,
            include=["documents", "metadatas"]
        )
    except Exception as e:
        return f"Error during retrieval: {e}", {"sources": [], "timings": {}}

    retrieval_time = t.time() - start_retrieval
    timings["retrieval_s"] = round(retrieval_time, 3)

    retrieved_docs = results["documents"][0]
    retrieved_meta = results["metadatas"][0]

    if not retrieved_docs or all(not doc.strip() for doc in retrieved_docs):
        return "Not found in crawled content", {"sources": [], "timings": timings}

    context_texts = "\n".join([
        f"Source: {meta['url']}\n{doc[:600]}"
        for meta, doc in zip(retrieved_meta[:8], retrieved_docs[:8])
    ])

    prompt = f"""
You are a factual extraction assistant.
Read the CONTEXT below and answer the QUESTION using ONLY the context.
If you see a phone number, email, or contact info, return it exactly.
If the context lists multiple items, count them carefully.
If not found, reply exactly: "Not found in crawled content."

CONTEXT: {context_texts}
QUESTION: {question}
FINAL ANSWER:
"""

    start_gen = t.time()
    try:
        
        answer = gpt_model.generate(prompt, max_tokens=120, temp=0.1, top_k=40)
    except Exception as e:
        return f"Error during generation: {e}", {"sources": [], "timings": timings}

    gen_time = t.time() - start_gen
    timings["generation_s"] = round(gen_time, 3)
    timings["total_s"] = round(retrieval_time + gen_time, 3)

    sources = [
        {"url": meta["url"], "snippet": doc[:200]}
        for meta, doc in zip(retrieved_meta, retrieved_docs)
    ]

    return answer.strip(), {"sources": sources, "timings": timings}




# ---------------------------
# GRADIO UI
# ---------------------------
with gr.Blocks() as demo:
    with gr.Tab("Crawl"):
        start_url_input = gr.Textbox(label="Start URL")
        second_url_input = gr.Textbox(label="Optional Second URL")
        crawl_btn = gr.Button("Start Crawl")
        crawl_output = gr.JSON(label="Crawl Result")
        crawl_btn.click(crawl_site_async, inputs=[start_url_input, second_url_input], outputs=[crawl_output])

    with gr.Tab("Index"):
        index_btn = gr.Button("Index Crawled Content")
        index_output = gr.JSON(label="Index Result")
        index_btn.click(index_site, outputs=[index_output])

    with gr.Tab("Ask"):
        question_input = gr.Textbox(label="Question", placeholder="Type your question here...", interactive=True)
        ask_btn = gr.Button("Ask Question")
        answer_output = gr.Textbox(label="Answer", lines=4)
        sources_output = gr.JSON(label="Sources")

        def handle_question(question):
            yield "Processing...", {"sources": []}
            answer, sources = ask_question_strict(question)
            yield answer, sources

        ask_btn.click(handle_question, inputs=[question_input], outputs=[answer_output, sources_output])

demo.launch()
if __name__ == "__main__":
    demo.launch()

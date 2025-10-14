import tldextract

def same_domain(start_url, candidate):
    start_domain = tldextract.extract(start_url).registered_domain
    candidate_domain = tldextract.extract(candidate).registered_domain
    return start_domain == candidate_domain

def chunk_text_words(text, size=500, overlap=50):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += size - overlap
    return chunks
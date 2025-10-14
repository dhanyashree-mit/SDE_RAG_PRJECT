import pytest
from utils import same_domain, chunk_text_words

def test_same_domain():
    assert same_domain("http://example.com/page1", "https://www.example.com/page2") == True

def test_chunk_text_words():
    text = "one two three four five six"
    chunks = chunk_text_words(text, size=5, overlap=2)
    assert chunks[0] == "one two three four five"

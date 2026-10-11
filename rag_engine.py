import os
import glob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge_base")

def init_knowledge_dir():
    """Creates local knowledge_base directory if it doesn't exist."""
    if not os.path.exists(KNOWLEDGE_DIR):
        os.makedirs(KNOWLEDGE_DIR)
        sample_path = os.path.join(KNOWLEDGE_DIR, "system_notes.txt")
        with open(sample_path, "w", encoding="utf-8") as f:
            f.write("Aven System Architecture: Level 5 introduces local RAG and semantic vector search.\n")
            f.write("Data Science Workspace: Python with FastAPI, SQLite, and Groq API.\n")

def get_relevant_memories(user_query: str, memories: list, top_k: int = 3) -> list:
    """Ranks long-term memories semantically against the user query using TF-IDF."""
    if not memories:
        return []
    
    fact_texts = [m["fact"] for m in memories]
    corpus = [user_query] + fact_texts
    
    try:
        vectorizer = TfidfVectorizer().fit_transform(corpus)
        vectors = vectorizer.toarray()
        query_vec = vectors[0:1]
        fact_vecs = vectors[1:]
        
        similarities = cosine_similarity(query_vec, fact_vecs)[0]
        
        scored = list(zip(similarities, memories))
        scored.sort(key=lambda x: x[0], reverse=True)
        
        relevant = [mem for score, mem in scored if score > 0.0]
        return relevant[:top_k] if relevant else memories[:top_k]
    except Exception as e:
        print(f"[MEMORY SEARCH ERROR]: {e}")
        return memories[:top_k]

def search_local_documents(query: str, top_k: int = 2) -> str:
    """Searches files inside ./knowledge_base using TF-IDF vector similarity."""
    init_knowledge_dir()
    files = glob.glob(os.path.join(KNOWLEDGE_DIR, "*.*"))
    text_chunks = []
    
    for file_path in files:
        filename = os.path.basename(file_path)
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
                for p in paragraphs:
                    text_chunks.append({"source": filename, "text": p})
        except Exception as e:
            print(f"[RAG READ ERROR] {filename}: {e}")
            
    if not text_chunks:
        return "No document content found in local knowledge base."
        
    chunk_texts = [c['text'] for c in text_chunks]
    corpus = [query] + chunk_texts
    
    try:
        vectorizer = TfidfVectorizer().fit_transform(corpus)
        vectors = vectorizer.toarray()
        query_vec = vectors[0:1]
        chunk_vecs = vectors[1:]
        
        similarities = cosine_similarity(query_vec, chunk_vecs)[0]
        
        scored_chunks = list(zip(similarities, text_chunks))
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        results = [f"[{c['source']}]\n{c['text']}" for score, c in scored_chunks[:top_k] if score > 0.0]
        
        if not results:
            return "No relevant information found matching query in local documents."
            
        return "\n\n---\n\n".join(results)
    except Exception as e:
        return f"Error executing knowledge base search: {str(e)}"
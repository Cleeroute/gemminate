import os
import faiss
import pickle

vector_dirs = [os.path.join("static/vector_stores", d) for d in os.listdir("static/vector_stores") if d.startswith("vs_")]
for vdir in vector_dirs:
    pkl_path = os.path.join(vdir, "index.pkl")
    if os.path.exists(pkl_path):
        with open(pkl_path, "rb") as f:
            index = pickle.load(f)
            # index is a tuple (docstore, index_to_docstore_id) or a VectorStore object?
            # It's Langchain FAISS.
            from langchain_community.vectorstores import FAISS
            from langchain_huggingface import HuggingFaceEmbeddings
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            vector_store = FAISS.load_local(vdir, embeddings, allow_dangerous_deserialization=True)
            for doc_id, doc in vector_store.docstore._dict.items():
                if "MATH_BLOCK" in doc.page_content:
                    print(f"FOUND IN {vdir}:")
                    print(doc.page_content[:200])
                    print("---")

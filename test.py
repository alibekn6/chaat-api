
from google.cloud import storage

client = storage.Client()
for bucket in client.list_buckets():
    print(bucket.name)


# You must use a separate storage solution for your PDFs.
# Recommended: Google Cloud Storage (GCS), AWS S3,
#  or another cloud storage provider.


# For MVP/testing, you could use local storage, but it’s not scalable or secure for production.
# How the flow works:
# User uploads a PDF to your FastAPI backend.
# Your backend stores the PDF in GCS (or S3, etc.) 
# and saves the file URL/path in your database.
# Your backend extracts text from the PDF, chunks it, and sends those chunks to OpenAI’s embeddings API.
# You store the resulting embeddings (vectors) in a vector database (e.g., ChromaDB, Pinecone, FAISS).
# When a user asks a question, you:
# Retrieve relevant chunks from your vector DB.
# Send those chunks + the user’s question to OpenAI’s chat/completions API.
# Return the answer to the user.
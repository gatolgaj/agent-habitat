import os
from google.cloud import storage
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import VertexAIEmbeddings
from langchain.vectorstores import Qdrant
import json

def process_and_store_files(folder_path):
    # Ensure the folder exists
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"The folder '{folder_path}' does not exist.")

    # List all files in the folder
    file_list = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

    # Check if there are any files in the folder
    if not file_list:
        raise FileNotFoundError(f"No files found in the folder '{folder_path}'.")

    for filename in file_list:
        file_path = os.path.join(folder_path, filename)
        print(f"Processing file: {file_path}")

        # Load and split the text from the file
        loader = TextLoader(file_path)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        documents = loader.load_and_split(text_splitter)

        # Generate embeddings
        embeddings = VertexAIEmbeddings("textembedding-gecko@001")

        # Store documents in Qdrant
        qdrant = Qdrant.from_documents(
            documents, embeddings,
            collection_name=os.getenv("COLLECTION_NAME"),
            url=os.getenv("QDRANT_URL"), 
            api_key=os.getenv("APIKEY"),
            shard_number=6,
            replication_factor=2
        )

        print(f"{filename} was successfully embedded")
        print(f"# of vectors = {len(documents)}")

    print("All files have been processed and stored in Qdrant.")
    return "ok"


folder_path = "output"
process_and_store_files(folder_path)
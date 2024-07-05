import os
import json
import weaviate
from weaviate.auth import AuthApiKey
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
from typing import List, Optional
import weaviate.classes as wvc
from dotenv import load_dotenv

load_dotenv()

def embed_text(texts: List[str], task: str = "RETRIEVAL_DOCUMENT", model_name: str = "text-embedding-004", dimensionality: Optional[int] = 256) -> List[List[float]]:
    """Embeds texts with a pre-trained, foundational model."""
    model = TextEmbeddingModel.from_pretrained(model_name)
    inputs = [TextEmbeddingInput(text, task) for text in texts]
    kwargs = dict(output_dimensionality=dimensionality) if dimensionality else {}
    embeddings = model.get_embeddings(inputs, **kwargs)
    return [embedding.values for embedding in embeddings]

def process_local_file(file_path: str):
    # Load and split text
    loader = TextLoader(file_path)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    documents = loader.load_and_split(text_splitter)

    print(documents)
    # Extract texts for embedding
    texts = [doc.page_content for doc in documents]
    embeddings = embed_text(texts)

    # Connect to Weaviate instance
    # client = weaviate.Client(
    #     url=os.getenv("WEAVIATE_URL"), 
    #     additional_headers={
    #         "X-OpenAI-Api-Key": os.getenv("WEAVIATE_API_KEY")
    #     }
    # )
    collection_name = os.getenv("COLLECTION_NAME")
    client = weaviate.connect_to_local()
    if(not client.collections.exists(collection_name)) :
         print("Collection Does not Exist ,")
         client.collections.create(
            collection_name,
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        )
   
    # Prepare data objects
    data_objects = []
    for doc, embedding in zip(documents, embeddings):
        data_object = {
            "text": doc.page_content,
            "metadata": doc.metadata
        }
        data_objects.append(wvc.data.DataObject(
            properties=data_object,
            vector=embedding
        ))

    # Insert data into Weaviate
    docCollection = client.collections.get(collection_name)
    docCollection.data.insert_many(data_objects) 

    print(f"File {file_path} was successfully embedded and stored in Weaviate.")
    print(f"# of vectors = {len(documents)}")

    query_vector = embed_text(["What are the Duties of Entry Level Accountant ?"]) [0]

    response = docCollection.query.near_vector(
        near_vector=query_vector,
        limit=2,
        return_metadata=wvc.query.MetadataQuery(certainty=True)
    )

    print(response)
    client.close()

if __name__ == "__main__":
    # Path to your local file
    file_path = "documents/test-file.txt"
    process_local_file(file_path)
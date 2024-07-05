import os
import weaviate
from weaviate.auth import AuthApiKey
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def drop_collection(collection_name: str):
    # Retrieve environment variables
    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_http_port = os.getenv("WEAVIATE_HTTP_PORT")
    weaviate_grpc_port = os.getenv("WEAVIATE_GRPC_PORT")

    # Check if environment variables are set
    if not weaviate_url or not weaviate_http_port or not weaviate_grpc_port:
        raise ValueError("Ensure WEAVIATE_URL, WEAVIATE_HTTP_PORT, and WEAVIATE_GRPC_PORT are set in the .env file")

    # Connect to Weaviate instance
    client = weaviate.connect_to_custom(
        http_host=weaviate_url,  # URL only, no http prefix
        http_port=int(weaviate_http_port),
        http_secure=False,  # Set to True if https
        grpc_host=weaviate_url,
        grpc_port=int(weaviate_grpc_port),  # Default is 50051, WCD uses 443
        grpc_secure=False,  # Edit as needed
    )

    # Check if the collection exists
    if client.collections.exists(collection_name):
        # Drop the collection
        client.collections.delete(collection_name)
        print(f"Collection '{collection_name}' was successfully dropped.")
    else:
        print(f"Collection '{collection_name}' does not exist.")

    # Close the client connection
    client.close()

if __name__ == "__main__":
    # Specify the collection name you want to drop
    collection_name = os.getenv("COLLECTION_NAME")
    if not collection_name:
        raise ValueError("Ensure COLLECTION_NAME is set in the .env file")
    drop_collection(collection_name)
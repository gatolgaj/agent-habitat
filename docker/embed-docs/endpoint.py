# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from flask import Flask, jsonify
from flask import request
import logging
import sys,os, time
from kubernetes import client, config, utils
import kubernetes.client
from kubernetes.client.rest import ApiException
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Qdrant
from google.cloud import storage
from langchain.document_loaders import TextLoader
from langchain_community.document_loaders import PyPDFLoader
import os
import weaviate
from weaviate.auth import AuthApiKey
from flask import request
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
from typing import List, Optional
import weaviate.classes as wvc
from google.cloud import storage



app = Flask(__name__)

def embed_text(texts: List[str], task: str = "RETRIEVAL_DOCUMENT", model_name: str = "text-embedding-004", dimensionality: Optional[int] = 256) -> List[List[float]]:
    """Embeds texts with a pre-trained, foundational model."""
    model = TextEmbeddingModel.from_pretrained(model_name)
    inputs = [TextEmbeddingInput(text, task) for text in texts]
    kwargs = dict(output_dimensionality=dimensionality) if dimensionality else {}
    embeddings = model.get_embeddings(inputs, **kwargs)
    return [embedding.values for embedding in embeddings]

@app.route('/check')
def message():
    return jsonify({"Message": "Hi there"})


@app.route('/', methods=['POST'])
def bucket():
    request_data = request.get_json()
    print(request_data)
    bucketname = request_data['bucket']
    filename = request_data['name']
    id = request_data['generation']
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucketname)
    blob = bucket.blob(filename)
    local_path = "/documents/" + filename
    blob.download_to_filename(local_path)

    # Load and split text
    loader = TextLoader(local_path)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
    documents = loader.load_and_split(text_splitter)

    print(documents)
    # Extract texts for embedding
    texts = [doc.page_content for doc in documents]
    embeddings = embed_text(texts)

    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_http_port = os.getenv("WEAVIATE_HTTP_PORT")
    weaviate_grpc_port = os.getenv("WEAVIATE_GRPC_PORT")
    weaviate_url_grpc = os.getenv("WEAVIATE_URL_GRPC")


    # Check if environment variables are set
    if not weaviate_url or not weaviate_http_port or not weaviate_grpc_port or not weaviate_url_grpc:
        raise ValueError("Ensure WEAVIATE_URL, WEAVIATE_HTTP_PORT, and WEAVIATE_GRPC_PORT are set in the .env file")

    # Connect to Weaviate instance
    client = weaviate.connect_to_custom(
        http_host=weaviate_url,  # URL only, no http prefix
        http_port=int(weaviate_http_port),
        http_secure=False,  # Set to True if https
        grpc_host=weaviate_url_grpc,
        grpc_port=int(weaviate_grpc_port),  # Default is 50051, WCD uses 443
        grpc_secure=False,  # Edit as needed
    )
    # Check and create collection if not exists
    collection_name = os.getenv("COLLECTION_NAME")
    if not client.collections.exists(collection_name):
        print("Collection does not exist, creating...")
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
    doc_collection = client.collections.get(collection_name)
    doc_collection.data.insert_many(data_objects)

    print(f"File {filename} was successfully embedded and stored in Weaviate.")
    print(f"# of vectors = {len(documents)}")
    client.close()

    return "ok"
# Set logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# # Setup K8 configs
# config.load_incluster_config()
# # [START gke_databases_qdrant_docker_embed_endpoint_job]
# def kube_create_job_object(name, container_image, bucket_name, f_name, namespace="qdrant", container_name="jobcontainer", env_vars={}):

#     body = client.V1Job(api_version="batch/v1", kind="Job")
#     body.metadata = client.V1ObjectMeta(namespace=namespace, name=name)
#     body.status = client.V1JobStatus()
    
#     template = client.V1PodTemplate()
#     template.template = client.V1PodTemplateSpec()
#     env_list = [
#         client.V1EnvVar(name="QDRANT_URL", value=os.getenv("QDRANT_URL")),
#         client.V1EnvVar(name="COLLECTION_NAME", value="training-docs"), 
#         client.V1EnvVar(name="FILE_NAME", value=f_name), 
#         client.V1EnvVar(name="BUCKET_NAME", value=bucket_name),
#         client.V1EnvVar(name="APIKEY", value_from=client.V1EnvVarSource(secret_key_ref=client.V1SecretKeySelector(key="api-key", name="qdrant-database-apikey"))), 
#     ]
    
#     container = client.V1Container(name=container_name, image=container_image, env=env_list)
#     template.template.spec = client.V1PodSpec(containers=[container], restart_policy='Never', service_account='embed-docs-sa')

#     body.spec = client.V1JobSpec(backoff_limit=3, ttl_seconds_after_finished=60, template=template.template)
#     return body
# # [END gke_databases_qdrant_docker_embed_endpoint_job]
# def kube_test_credentials():
#     try: 
#         api_response = api_instance.get_api_resources()
#         logging.info(api_response)
#     except ApiException as e:
#         print("Exception when calling API: %s\n" % e)

# def kube_create_job(bckt, f_name, id):
#     container_image = os.getenv("JOB_IMAGE")
#     name = "docs-embedder" + id
#     body = kube_create_job_object(name, container_image, bckt, f_name)
#     v1=client.BatchV1Api()
#     try: 
#         v1.create_namespaced_job("qdrant", body, pretty=True)
#     except ApiException as e:
#         print("Exception when calling BatchV1Api->create_namespaced_job: %s\n" % e)
#     return

if __name__ == '__main__':
    app.run('0.0.0.0', port=5001, debug=True)

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



app = Flask(__name__)
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
    blob.download_to_filename("/documents/" + filename)
    # [END gke_databases_qdrant_docker_embed_docs_retrieval]

    # [START gke_databases_qdrant_docker_embed_docs_split]
    loader = TextLoader("/documents/" + filename)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    documents = loader.load_and_split(text_splitter)
    # [END gke_databases_qdrant_docker_embed_docs_split]

    # [START gke_databases_qdrant_docker_embed_docs_embed]
    embeddings = VertexAIEmbeddings("textembedding-gecko@001")
    # [END gke_databases_qdrant_docker_embed_docs_embed]

    # [START gke_databases_qdrant_docker_embed_docs_storage]
    qdrant = Qdrant.from_documents(
        documents, embeddings,
        collection_name=os.getenv("COLLECTION_NAME"),
        url=os.getenv("QDRANT_URL"), 
        api_key=os.getenv("APIKEY"),
        shard_number=6,
        replication_factor=2
    )
    # [END gke_databases_qdrant_docker_embed_docs_storage]
    print(filename + " was successfully embedded") 
    print(f"# of vectors = {len(documents)}")
    return "ok"

# Set logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# Setup K8 configs
config.load_incluster_config()
# [START gke_databases_qdrant_docker_embed_endpoint_job]
def kube_create_job_object(name, container_image, bucket_name, f_name, namespace="qdrant", container_name="jobcontainer", env_vars={}):

    body = client.V1Job(api_version="batch/v1", kind="Job")
    body.metadata = client.V1ObjectMeta(namespace=namespace, name=name)
    body.status = client.V1JobStatus()
    
    template = client.V1PodTemplate()
    template.template = client.V1PodTemplateSpec()
    env_list = [
        client.V1EnvVar(name="QDRANT_URL", value=os.getenv("QDRANT_URL")),
        client.V1EnvVar(name="COLLECTION_NAME", value="training-docs"), 
        client.V1EnvVar(name="FILE_NAME", value=f_name), 
        client.V1EnvVar(name="BUCKET_NAME", value=bucket_name),
        client.V1EnvVar(name="APIKEY", value_from=client.V1EnvVarSource(secret_key_ref=client.V1SecretKeySelector(key="api-key", name="qdrant-database-apikey"))), 
    ]
    
    container = client.V1Container(name=container_name, image=container_image, env=env_list)
    template.template.spec = client.V1PodSpec(containers=[container], restart_policy='Never', service_account='embed-docs-sa')

    body.spec = client.V1JobSpec(backoff_limit=3, ttl_seconds_after_finished=60, template=template.template)
    return body
# [END gke_databases_qdrant_docker_embed_endpoint_job]
def kube_test_credentials():
    try: 
        api_response = api_instance.get_api_resources()
        logging.info(api_response)
    except ApiException as e:
        print("Exception when calling API: %s\n" % e)

def kube_create_job(bckt, f_name, id):
    container_image = os.getenv("JOB_IMAGE")
    name = "docs-embedder" + id
    body = kube_create_job_object(name, container_image, bckt, f_name)
    v1=client.BatchV1Api()
    try: 
        v1.create_namespaced_job("qdrant", body, pretty=True)
    except ApiException as e:
        print("Exception when calling BatchV1Api->create_namespaced_job: %s\n" % e)
    return

if __name__ == '__main__':
    app.run('0.0.0.0', port=5001, debug=True)

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

from langchain_google_vertexai import ChatVertexAI
from langchain.prompts import ChatPromptTemplate
from langchain_google_vertexai import VertexAIEmbeddings
from langchain.memory import ConversationBufferWindowMemory
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
import streamlit as st
import os
import weaviate
from weaviate.auth import AuthApiKey
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
from typing import List, Optional
import weaviate.classes as wvc
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

# [START gke_databases_qdrant_docker_chat_model]
vertexAI = ChatVertexAI(model_name="gemini-pro", streaming=True, convert_system_message_to_human=True)
prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant who helps in finding answers to questions using the provided context."),
        ("human", """
        The answer should be based on the text context given in "text_context" and the conversation history given in "conversation_history" along with its Caption: \n
        Base your response on the provided text context and the current conversation history to answer the query.
        Select the most relevant information from the context.
        Generate a draft response using the selected information. Remove duplicate content from the draft response.
        Generate your final response after adjusting it to increase accuracy and relevance.
        Now only show your final response!
        If you do not know the answer or context is not relevant, response with "I don't know".

        text_context:
        {context}

        conversation_history:
        {history}

        query:
        {query}
        """),
    ]
)

# embedding_model = VertexAIEmbeddings("textembedding-gecko@001")
# # [END gke_databases_qdrant_docker_chat_model]

# # [START gke_databases_qdrant_docker_chat_client]
# client = QdrantClient(
#     url=os.getenv("QDRANT_URL"),
#     api_key=os.getenv("APIKEY"),
# )
collection_name = os.getenv("COLLECTION_NAME")
    # Connect to Weaviate instance
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
docCollection = client.collections.get(collection_name)
# qdrant = Qdrant(client, collection_name, embeddings=embedding_model)
# [END gke_databases_qdrant_docker_chat_client]
def format_docs(docs):
    return "\n\n".join([d.properties['text'] for d in docs.objects])

def embed_text(texts: List[str], task: str = "RETRIEVAL_DOCUMENT", model_name: str = "text-embedding-004", dimensionality: Optional[int] = 256) -> List[List[float]]:
    """Embeds texts with a pre-trained, foundational model."""
    model = TextEmbeddingModel.from_pretrained(model_name)
    inputs = [TextEmbeddingInput(text, task) for text in texts]
    kwargs = dict(output_dimensionality=dimensionality) if dimensionality else {}
    embeddings = model.get_embeddings(inputs, **kwargs)
    return [embedding.values for embedding in embeddings]

st.title("🤖 Chatbot")
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "ai", "content": "How can I help you?"}]
# [START gke_databases_qdrant_docker_chat_session]
if "memory" not in st.session_state:
    st.session_state["memory"] = ConversationBufferWindowMemory(
        memory_key="history",
        ai_prefix="Bob",
        human_prefix="User",
        k=3,
    )
# [END gke_databases_qdrant_docker_chat_session]
# [START gke_databases_qdrant_docker_chat_history]
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
# [END gke_databases_qdrant_docker_chat_history]
if chat_input := st.chat_input():
    with st.chat_message("human"):
        st.write(chat_input)
        st.session_state.messages.append({"role": "human", "content": chat_input})

    chat_input_vector = embed_text([chat_input])[0]
    found_docs = docCollection.query.near_vector(
        near_vector=chat_input_vector,
        limit=2,
        return_metadata=wvc.query.MetadataQuery(certainty=True)
    )
    context = format_docs(found_docs)

    prompt_value = prompt_template.format_messages(name="Bob", query=chat_input, context=context, history=st.session_state.memory.load_memory_variables({}))
    with st.chat_message("ai"):
        with st.spinner("Typing..."):
            content = ""
            with st.empty():
                for chunk in vertexAI.stream(prompt_value):
                    content += chunk.content
                    st.write(content)
            st.session_state.messages.append({"role": "ai", "content": content})

    st.session_state.memory.save_context({"input": chat_input}, {"output": content})


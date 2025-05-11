from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import requests
import json
import bs4
from langchain import hub
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import START, StateGraph
from typing_extensions import List, TypedDict
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain.chat_models import init_chat_model
import vertexai
from langsmith import Client
import random
import urllib.parse

load_dotenv()

app = Flask(__name__)
CORS(app) 

#api keys
API_KEYS = {
    'gemini': os.getenv('GOOGLE_API_KEY'),
    'vertex': os.getenv('VERTEX_API_KEY'),
    'projectid': os.getenv('PROJECT_ID'),
    'location': os.getenv('LOCATION'),
    'langsmith': os.getenv('LANGSMITH_API_KEY')
}

#llm model
model = init_chat_model("gemini-2.0-flash", model_provider="google_genai")
#database and splitter for embeddings
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
vertexai.init(project=API_KEYS['projectid'], location=API_KEYS['location'], api_key=API_KEYS['vertex'])
embeddings = VertexAIEmbeddings(model="text-embedding-004")
vector_store = InMemoryVectorStore(embeddings)
#base prompt structure for question-answering
#prompt = hub.pull("rlm/rag-prompt")
client = Client(api_key=API_KEYS['langsmith'])
prompt = client.pull_prompt("prathiks/steamragprompt")
summary_prompt = client.pull_prompt("prathiks/steamsummaryprompt")
#cursor index and app idfor getting additional reviews
cursoridx = 0
cursor = urllib.parse.quote("")
saved_app_id = 0


class State(TypedDict):
    question: str
    context: List[Document]
    answer: str


#rag retrieval search
def retrieve(state: State):
    context_docs = []
    if(state["question"] == "summary"):
        retrieved_docs = vector_store.similarity_search(state["question"],k=10)
        context_docs+=retrieved_docs
    else:
        #retrieving 5 most relevant docs
        retrieved_docs = vector_store.similarity_search(state["question"],k=5)
        context_docs+=retrieved_docs
        #adding random docs to context for better attention (based on frontier paper topic I studied)
        random_docs = vector_store.similarity_search("random", k=100)
        #3 docs at random
        if random_docs:
            for i in range(3):
                random_doc = random.choice(random_docs)
                context_docs.append(random_doc)
    return {"context": context_docs}

#rag generation
def generate(state: State):
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    
    if(state["question"] == "summary"):
        messages = summary_prompt.invoke({"question": state["question"], "context": docs_content})
    else:
        messages = prompt.invoke({"question": state["question"], "context": docs_content})
    response = model.invoke(messages)
    return {"answer": response.content}

#compiles rag graph
graph_builder = StateGraph(State).add_sequence([retrieve, generate])
graph_builder.add_edge(START, "retrieve")
graph = graph_builder.compile()

#requests reviews from steam api
def get_reviews(app_id, num=100):
    global cursor, cursoridx
    url = f"https://store.steampowered.com/appreviews/{app_id}"
    if cursoridx == 0:
        params = {
            "json": 1,
            "language": "english",
            "filter": "all",
            "num_per_page": num
        }
    else:
        params = {
            "json": 1,
            "language": "english",
            "filter": "all",
            "num_per_page": num,
            "cursor": cursor
        }
    response = requests.get(url, params=params)
    data = response.json()
    reviews = data.get("reviews", [])
    cursor = urllib.parse.quote(data.get("cursor"))
    cursoridx += len(reviews)
    print(cursoridx)
    return [r["review"] for r in reviews]

#gets llm text response to send to frontend
def generateResponse(message):
    if(message == "summary"):
        llmResponse = graph.invoke({"question": message})    
        return {
                "response": llmResponse["answer"],
                "status": "success"
        }
    else:
        llmResponse = graph.invoke({"question": message})
        if(llmResponse["answer"] == "Unable to find answer in retrieved reviews"):
            return {
                "response": llmResponse["answer"],
                "status": "success"
            }
        review_text = vector_store.similarity_search(message, k=1)
        return {
                "response": llmResponse["answer"],
                "review_text": review_text[0].page_content,
                "status": "success"
        }

def searchApp(query):
    try:
        url = "https://store.steampowered.com/api/storesearch/"
        params = {
            "term": query,
            "cc": "US",
            "l": "en"
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            e = Exception("Failed to fetch from Steam API.")
            return {"error": str(e)}, 500
        
        data = response.json()
        results = data.get("items", [])
        #print(results)
        return {"results":[{"id": item["id"], "title": item["name"], 
                "thumbnail": item["tiny_image"],} for item in results],
                "status": "success"}
    except Exception as e:
        return {"error": str(e)}, 500

#finds app info and reviews
#populates vector store and generates summary
def findAppInfo(app_id):
    global vector_store, saved_app_id, cursoridx
    try:
        #get reviews
        cursoridx = 0
        reviews = get_reviews(app_id)
        saved_app_id = app_id
        
        docs = [Document(page_content=review) for review in reviews]
        all_splits = text_splitter.split_documents(docs)
        vector_store = InMemoryVectorStore(embedding=embeddings)
        _ = vector_store.add_documents(documents=all_splits)

        summary = generateResponse("summary")
        print(summary)

        #request app details
        url = f"https://store.steampowered.com/api/appdetails"
        params = {
            "appids": app_id,
            "cc": "US",
            "l": "en"
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return {"error": "Failed to fetch app details"}, 500
    
        data = response.json()
        app_data = data.get(str(app_id), {}).get("data", {})
        #print(app_data) 
        #returns app details to frontend
        return {
            "status": "success",
            "details": {
                "name": app_data.get("name", ""),
                "description": app_data.get("short_description", ""),
                "price": app_data.get("price_overview", {}).get("final_formatted", "Free"),
                "categories": [cat["description"] for cat in app_data.get("categories", [])],
                "genres": [genre["description"] for genre in app_data.get("genres", [])],
                "header_image": app_data.get("header_image", ""),
                "website": app_data.get("website", ""),
                "developers": app_data.get("developers", []),
                "publishers": app_data.get("publishers", []),
                "summary": summary['response']
            }
        }
    except Exception as e:
        return {"error": str(e)}, 500
    
#requests additional reviews from steam api and regenerates query
def additionalReviews(query):
    try:
        additional_reviews = get_reviews(saved_app_id)
        if(len(additional_reviews) == 0):
            raise Exception("No additional reviews found")
        docs = [Document(page_content=review) for review in additional_reviews]
        all_splits = text_splitter.split_documents(docs)
        _ = vector_store.add_documents(documents=all_splits)

        return generateResponse(query)
    
    except Exception as e:
        return {"error": str(e)}, 500

#handles getting message from llm to frontend
def handleSendMessage(message):
    try:
        response = generateResponse(message)
        return response
    except Exception as e:
        return {"error": str(e)}, 500

#returns status of API keys
def requestAPIKeys():
    return {
        "gemini": bool(API_KEYS['gemini']),
        "langsmith": bool(API_KEYS['langsmith']),
        "vertex": bool(API_KEYS['vertex']),
        "projectid": bool(API_KEYS['projectid']),
        "location": bool(API_KEYS['location']),
        "status": "success"
    }

# API Routes
@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    if not data or 'message' not in data:
        return {"error": "No message provided"}, 400
    return generateResponse(data['message'])

@app.route('/api/search', methods=['POST'])
def search():
    data = request.json
    if not data or 'query' not in data:
        return {"error": "No search query provided"}, 400
    return searchApp(data['query'])

@app.route('/api/find', methods=['POST'])
def find():
    data = request.json
    if not data or 'app_id' not in data:
        return {"error": "No app ID provided"}, 400
    return findAppInfo(data['app_id'])

@app.route('/api/message', methods=['POST'])
def message():
    data = request.json
    if not data or 'message' not in data:
        return {"error": "No message provided"}, 400
    return handleSendMessage(data['message'])

@app.route('/api/keys', methods=['GET'])
def keys():
    return requestAPIKeys()

@app.route('/api/additional-reviews', methods=['POST'])
def get_additional_reviews():
    data = request.json
    if not data or 'query' not in data:
        return {"error": "No query provided"}, 400
    return additionalReviews(data['query'])

if __name__ == '__main__':
    app.run(debug=True, port=5000) 
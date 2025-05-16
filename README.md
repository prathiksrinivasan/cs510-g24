# cs510-g24
CS 510 Group 24 project

# Overview
Steam RAG is a retrieval augmented generation tool that allows you to search through information from steam reviews in your browser
# Installation 

Install Python (Version used: 3.9.7)

Install Node.js

After cloning the repository, run 'npm install' in the main folder.

Navigate to /backend/ and run 'pip install -r requirements.txt'

Create a file called .env in the backend folder.

Generate an API key for google gemini, and add GOOGLE_API_KEY=<your_api_key> in .env

Generate an API key for google VertexAI embeddings, and add VERTEXAI_API_KEY=<your_api_key> in .env

Create a VertexAI project, and add PROJECT_ID="your project id" and LOCATION="your project location" to .env

Generate an API key for LangSmith, and add LANGSMITH_API_KEY=<your_api_key> to .env

In the main folder, use "npm run" to run the front-end

In the /backend/ folder, use "python app.py" to run the back-end in another terminal
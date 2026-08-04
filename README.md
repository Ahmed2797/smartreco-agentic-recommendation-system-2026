# SmartReco Build Challenge 2026 – AI Behavioral Recommendation Agent

An Agentic AI-powered recommendation platform that understands user behavior, retrieves the most relevant products using RAG, and generates persuasive personalized recommendations with Mesh API.

## Setup Environment

```bash

conda create -n smartreco python=3.10

conda activate smartreco

pip install -r requirements.txt


## Configure Environment Variables

MESH_API_KEY = ""
SUBMISSION_TOKEN = ""

PINECONE_API_KEY = ""
OPENAI_API_KEY = ""

PINECONE_INDEX_NAME = "smartreco-products"
DATABASE_URL = "sqlite:///./Data/smartreco.db"
SECRET_KEY = ""

# LangSmith Observability Tracking
LANGSMITH_TRACING = False
LANGSMITH_ENDPOINT = "https://api.smith.langchain.com"
LANGSMITH_API_KEY = ""
LANGSMITH_PROJECT = "smartreco-build-challenge-2026"

# Email SMTP Configuration
SMTP_SERVER =smtp.gmail.com
SMTP_PORT =587
SMTP_USER =your_email@gmail.com
SMTP_PASSWORD =your_app_password_here
SENDER_EMAIL =your_email@gmail.com


AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""
AWS_ECR_LOGIN_URI = ""
ECR_REPOSITORY_NAME = 'rag'
AWS_REGION = "us-east-1"
AWS_DEFAULT_REGION = "us-east-1"
BUCKET_NAME = "rag-model-bucket-2026"
```

### RUN Terminal

```bash
python -m Data.mock_data
## python seed.py ## optional
uvicorn main:app --reload


```

### Observability with LangSmith

- Integrated **LangSmith tracing** across all LangGraph reasoning nodes (`analyze_behavior`, `retrieve_products`, `evaluate_and_refine`, `generate_persuasive_narrative`).
- Allows end-to-end inspection of state transitions, vector retrieval quality, and prompt token usage.

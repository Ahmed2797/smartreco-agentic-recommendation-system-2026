#!/bin/bash

# ==========================================
# SmartReco Build Challenge 2026
# Project Structure Generator
# ==========================================

# PROJECT_NAME="smartreco-build-challenge-2026"

# echo "Creating project: $PROJECT_NAME"

# # Create root directory
# mkdir -p $PROJECT_NAME
# cd $PROJECT_NAME || exit


# ================================
# Root Files
# ================================

touch app.py
touch main.py
touch requirements.txt
touch README.md
touch .env
touch .gitignore


# ================================
# Data
# ================================

mkdir -p Data
touch Data/sample_products.json
touch Data/smartreco.db


# ================================
# Research
# ================================

mkdir -p research

touch research/ai_rag_init.ipynb


# ================================
# Frontend
# ================================

mkdir -p frontend/templates
mkdir -p frontend/static/{css,js,images}


# HTML Templates

touch frontend/templates/login.html
touch frontend/templates/register.html
touch frontend/templates/dashboard.html
touch frontend/templates/admin.html
touch frontend/templates/recommendations.html


# JavaScript

touch frontend/static/js/tracker.js


# ================================
# Source Package
# ================================

mkdir -p src


# Create __init__.py

touch src/__init__.py


# ================================
# Config
# ================================

mkdir -p src/config

touch src/config/config.py
touch src/config/settings.py


# ================================
# Database
# ================================

mkdir -p src/database

touch src/database/db.py
touch src/database/models.py
touch src/database/crud.py


# ================================
# LLM / Chat Model
# ================================

mkdir -p src/chatmodel

touch src/chatmodel/mesh_client.py
touch src/chatmodel/llm.py


# ================================
# Embeddings + Vector Store
# ================================

mkdir -p src/embeddings

touch src/embeddings/embedding.py
touch src/embeddings/vector_store.py


# ================================
# Prompt Engineering
# ================================

mkdir -p src/prompt

touch src/prompt/recommendation_prompt.py
touch src/prompt/system_prompt.py


# ================================
# Pipelines
# ================================

mkdir -p src/pipeline

touch src/pipeline/recommendation_pipeline.py
touch src/pipeline/tracking_pipeline.py
touch src/pipeline/retrieval_pipeline.py


# ================================
# AI Agents
# ================================

mkdir -p src/agent

touch src/agent/recommendation_agent.py
touch src/agent/langgraph_agent.py


# ================================
# API Routes
# ================================

mkdir -p src/routes

touch src/routes/auth.py
touch src/routes/admin.py
touch src/routes/products.py
touch src/routes/tracking.py
touch src/routes/recommendations.py


# ================================
# Scheduler
# ================================

mkdir -p src/scheduler

touch src/scheduler/scheduler.py


# ================================
# Utils
# ================================

mkdir -p src/utils

touch src/utils/logger.py
touch src/utils/helper.py


# ================================
# Services
# ================================

mkdir -p src/services

touch src/services/product_service.py
touch src/services/tracking_service.py
touch src/services/recommendation_service.py



# ================================
# Add Python package files
# ================================

find src -type d -exec touch {}/__init__.py \;


echo ""
echo "=========================================="
echo "Project structure created successfully!"
echo "Location: $(pwd)"
echo "=========================================="

## bash template.sh
## tree smartreco-build-challenge-2026

# Dating AI Engine

AI-powered dating preference learning system that analyzes user choices across 3 phases to generate personalized recommendations.

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Database Setup](#database-setup)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Testing](#testing)

## ✨ Features

- **3-Phase Learning System**: Progressive refinement of user preferences
- **Face Recognition**: FaceNet-based facial feature extraction
- **Personalized Recommendations**: Cosine similarity-based matching
- **Token-Based Authentication**: Integration with main backend system
- **Batch Choice Submission**: Submit 20 choices per phase
- **RESTful API**: Comprehensive API with FastAPI

## 🏗️ Architecture

```
dating-ai-engine/
├── app/
│   ├── core/              # Core functionality
│   │   ├── config.py      # Configuration
│   │   ├── database.py    # Database connection
│   │   ├── auth_dependency.py  # Authentication
│   │   └── exception.py   # Custom exceptions
│   ├── models/            # SQLAlchemy models
│   │   ├── user.py
│   │   ├── user_image.py
│   │   ├── pool_image.py
│   │   ├── user_choice.py
│   │   └── recommendation.py
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   │   ├── auth_service.py
│   │   ├── face_processing_service.py
│   │   ├── recommendation_service.py
│   │   └── user_choice_service.py
│   ├── routes/            # API routes
│   └── middleware/        # Custom middleware
├── migrations/            # Alembic migrations
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
└── .env                  # Environment variables
```

## 📦 Prerequisites

- Python 3.10+
- PostgreSQL 14+ with pgvector extension
- Docker & Docker Compose (optional)
- CUDA-compatible GPU (optional, for faster face processing)

## 🚀 Installation

### 1. Clone Repository

```bash
git clone https://github.com/your-repo/dating-ai-engine.git
cd dating-ai-engine
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Additional ML Dependencies

```bash
# For face recognition
pip install facenet-pytorch torch torchvision

# For PostgreSQL with pgvector
pip install psycopg2-binary pgvector
```

## 🗄️ Database Setup

### Option 1: Using Docker Compose (Recommended)

```bash
# Start PostgreSQL with pgvector
docker-compose up -d db

# Verify database is running
docker-compose ps
```

### Option 2: Manual PostgreSQL Setup

```bash
# Install PostgreSQL 14+
# Install pgvector extension

# Create database
psql -U postgres
CREATE DATABASE dating_ai_engine;

# Enable pgvector extension
\c dating_ai_engine
CREATE EXTENSION vector;
```

### Run Migrations

```bash
# Initialize Alembic (if not already done)
alembic init migrations

# Generate migration
alembic revision --autogenerate -m "init db"

# Run all migrations
alembic upgrade head

# Check current migration version
alembic current

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```

### Migration Commands Reference

```bash
# Create new migration
alembic revision -m "description"

# Auto-generate migration from models
alembic revision --autogenerate -m "description"

# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade <revision_id>

# Downgrade to previous
alembic downgrade -1

# Show migration history
alembic history

# Show current revision
alembic current
```

## ⚙️ Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/dating_ai_engine
PG_PORT=5432
PG_VOLUME=./pgdata
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=dating_ai_engine

# Main Backend Integration
DATING_APP_BASE_URL=https://api.your-main-backend.com
DATING_APP_IMAGE_BASE_URL=https://images.your-main-backend.com
DATING_APP_API_KEY=your_api_key_here
DATING_APP_TIMEOUT=30

# ML Settings
MIN_FACE_CONFIDENCE=0.8
EMBEDDING_DIM=512
SIMILARITY_THRESHOLD=0.5

# Application
PROFILES_PER_PHASE=20
IMAGE_DIR=./data/images
MODEL_DIR=./app/ml/models
DATASET_PATH=../dataset/ALL/ALL
```

### Start

```bash
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Configuration Options

| Variable               | Description                       | Default  |
| ---------------------- | --------------------------------- | -------- |
| `DATABASE_URL`         | PostgreSQL connection string      | Required |
| `DATING_APP_BASE_URL`  | Main backend API URL              | Required |
| `MIN_FACE_CONFIDENCE`  | Minimum face detection confidence | 0.8      |
| `EMBEDDING_DIM`        | Face embedding dimensions         | 512      |
| `SIMILARITY_THRESHOLD` | Minimum similarity for reco       |

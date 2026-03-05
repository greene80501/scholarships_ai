# SchoolSmart.ai - AI-Powered Scholarship Discovery Platform

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An intelligent scholarship matching platform that helps students discover and apply for educational funding opportunities. Features an AI-powered advisor that provides personalized scholarship recommendations through natural language conversations.

---

## Overview

SchoolSmart.ai connects students with relevant scholarship opportunities using a dual approach:

1. **AI Scholarship Advisor**: A conversational AI that understands student profiles and recommends matching scholarships from a curated knowledge base
2. **Advanced Search**: Traditional filtering and search capabilities for direct database exploration

The platform uses Retrieval-Augmented Generation (RAG) to provide accurate, context-aware scholarship recommendations based on field of study, education level, GPA, demographics, and other eligibility criteria.

---

## Key Features

### AI-Powered Scholarship Recommendations
- **Conversational Interface**: Natural language chat for scholarship discovery
- **Profile-Aware Matching**: Considers field of study, education level, GPA, and demographics
- **RAG-Based Responses**: Uses LlamaIndex with Together AI (Llama 3.3 70B) for intelligent recommendations
- **Persistent Context**: Maintains conversation history for personalized advice

### Comprehensive Scholarship Database
- **Large Dataset**: Pre-populated with extensive scholarship opportunities
- **Structured Data**: Each scholarship includes eligibility requirements, deadlines, award amounts, and application links
- **Inferred Attributes**: Automatic categorization by field of study, education level, and demographic requirements

### Advanced Search and Filtering
- **Multi-Criteria Search**: Filter by field of study, education level, GPA requirements, demographics, and keywords
- **Real-Time Results**: Fast SQLite-powered search with instant results
- **Bookmarking**: Save interesting scholarships for later review

### User Management
- **Secure Authentication**: Password hashing with Werkzeug security
- **Session Management**: Flask-based user sessions with persistent login
- **Admin Dashboard**: User management capabilities for administrators
- **Bookmark Persistence**: User-specific scholarship bookmarks stored in database

### Modern Web Interface
- **Responsive Design**: Mobile and desktop compatible
- **Interactive UI**: Dynamic scholarship cards with detailed modals
- **Real-Time Statistics**: Dashboard showing total scholarships and funding available
- **Dark/Light Mode**: Theme switching for user preference

---

## Technology Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │   Web Browser   │  │  Chat Interface │  │   Bookmark System   │  │
│  │   (HTML/CSS/JS) │  │   (AI Advisor)  │  │   (User Features)   │  │
│  └────────┬────────┘  └────────┬────────┘  └──────────┬──────────┘  │
└───────────┼────────────────────┼──────────────────────┼─────────────┘
            │                    │                      │
┌───────────▼────────────────────▼──────────────────────▼─────────────┐
│                         APPLICATION LAYER                            │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                      Flask Web Server                           │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────┐  │  │
│  │  │  Auth Module │ │ Search Utils │ │    AI Advisor (RAG)    │  │  │
│  │  │   (auth.py)  │ │(search_utils)│ │   (ai_advisor.py)      │  │  │
│  │  └──────────────┘ └──────────────┘ └────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
└───────────────────────┬───────────────────────┬──────────────────────┘
                        │                       │
┌───────────────────────▼───────┐  ┌───────────▼───────────┐
│       DATA STORAGE            │  │    AI/ML SERVICES     │
│                               │  │                       │
│  ┌────────────────────────┐   │  │  ┌─────────────────┐  │
│  │   Scholarships DB      │   │  │  │  LlamaIndex     │  │
│  │   (SQLite - 100MB+)    │   │  │  │  (RAG System)   │  │
│  │                        │   │  │  └────────┬────────┘  │
│  │  - 1000+ scholarships  │   │  │           │           │
│  │  - Full-text search    │   │  │  ┌────────▼────────┐  │
│  │  - JSON attributes     │   │  │  │  Together AI    │  │
│  └────────────────────────┘   │  │  │  (Llama 3.3 70B)│  │
│                               │  │  └─────────────────┘  │
│  ┌────────────────────────┐   │  │                       │
│  │   Users DB             │   │  │  ┌─────────────────┐  │
│  │   (SQLite)             │   │  │  │  HuggingFace    │  │
│  │                        │   │  │  │  Embeddings     │  │
│  │  - User accounts       │   │  │  │  (BAAI/bge)     │  │
│  │  - Bookmarks           │   │  │  └─────────────────┘  │
│  │  - Session data        │   │  │                       │
│  └────────────────────────┘   │  └───────────────────────┘
└───────────────────────────────┘
```

### Core Technologies

| Component | Technology |
|-----------|------------|
| **Backend Framework** | Python 3.8+, Flask 2.0+ |
| **Databases** | SQLite (scholarships.db, users.db) |
| **AI/ML Stack** | LlamaIndex, Together AI API, HuggingFace Transformers |
| **LLM Model** | Meta Llama 3.3 70B Instruct Turbo |
| **Embeddings** | BAAI/bge-small-en-v1.5 |
| **Authentication** | Werkzeug Security (password hashing) |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Styling** | Custom CSS with CSS variables |

---

## Prerequisites

### Required Software
- **Python 3.8 or higher** - [Download](https://www.python.org/downloads/)
- **Git** - [Download](https://git-scm.com/downloads)
- **Together AI API Key** - [Get one free](https://www.together.ai/)

### System Requirements
- **OS**: Windows 10/11, macOS, or Linux
- **RAM**: Minimum 4GB (8GB recommended for AI features)
- **Storage**: ~500MB free space (including database)
- **Internet**: Required for AI advisor functionality (Together AI API)

---

## Installation and Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/greene80501/scholarships_ai.git
cd scholarships_ai
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install flask torch llama-index llama-index-llms-openai-like llama-index-embeddings-huggingface werkzeug
```

Or install from requirements.txt (create one if needed):

```txt
flask>=2.3.0
torch>=2.0.0
llama-index>=0.10.0
llama-index-llms-openai-like>=0.1.0
llama-index-embeddings-huggingface>=0.2.0
werkzeug>=2.3.0
```

### Step 4: Configure Environment Variables

Set your Together AI API key as an environment variable:

```bash
# Windows PowerShell
$env:TOGETHER_API_KEY = "your_together_ai_api_key_here"
$env:FLASK_SECRET_KEY = "your_secret_key_here"

# Windows CMD
set TOGETHER_API_KEY=your_together_ai_api_key_here
set FLASK_SECRET_KEY=your_secret_key_here

# macOS/Linux
export TOGETHER_API_KEY="your_together_ai_api_key_here"
export FLASK_SECRET_KEY="your_secret_key_here"
```

### Step 5: Verify Database Files

Ensure the database files exist:

```
scholarships_ai/
├── scholarships.db          # Main scholarship database (~104MB)
├── users.db                 # User accounts and bookmarks
└── data/                    # RAG knowledge base documents
    └── (JSON files for AI advisor)
```

### Step 6: Run the Application

```bash
python app.py
```

The application will be available at: `http://localhost:5000`

---

## Project Structure

```
scholarships_ai/
├── app.py                      # Main Flask application entry point
├── auth.py                     # Authentication module (users.db management)
├── ai_advisor.py               # AI RAG system for scholarship recommendations
├── search_utils.py             # Search utilities and database interface
├── scholarships.db             # SQLite database with scholarship data
├── users.db                    # SQLite database for user accounts
│
├── data/                       # RAG knowledge base directory
│   └── (scholarship JSON files for AI context)
│
├── storage_ai_advisor/         # LlamaIndex persistent storage
│   └── (vector index cache)
│
├── static/                     # Static assets
│   ├── css/
│   │   └── styles.css          # Main stylesheet
│   ├── js/
│   │   └── (JavaScript files)
│   └── images/
│
└── templates/                  # Jinja2 HTML templates
    ├── index.html              # Landing page
    ├── search.html             # Scholarship search page
    ├── ai-recommend.html       # AI advisor chat interface
    ├── bookmarks.html          # User bookmarks page
    ├── login.html              # Login page
    ├── register.html           # Registration page
    ├── admin.html              # Admin dashboard
    └── header.html             # Navigation header component
```

---

## How It Works

### AI Advisor Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Student   │───▶│   Natural   │───▶│   Profile   │───▶│    RAG      │
│   Query     │    │   Language  │    │  Extraction │    │   Query     │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                 │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐           │
│   Display   │◀───│  Matched    │◀───│  Together   │◀──────────┘
│ Scholarship │    │ Scholarships│    │  AI (Llama) │
│   Cards     │    │   from DB   │    │  Response   │
└─────────────┘    └─────────────┘    └─────────────┘
```

1. **User Input**: Student describes their profile or asks for recommendations
2. **Context Analysis**: System extracts field of study, education level, GPA, and demographics
3. **RAG Retrieval**: LlamaIndex searches the scholarship knowledge base
4. **AI Processing**: Together AI (Llama 3.3 70B) generates personalized recommendations
5. **Database Lookup**: Matching scholarships are retrieved from SQLite database
6. **Results Display**: Scholarship cards are presented with full details

### Search Workflow

1. **Filter Application**: User selects criteria (field, level, GPA, etc.)
2. **SQL Query Generation**: Dynamic SQL query built from filters
3. **Database Execution**: SQLite query with optional full-text search
4. **Attribute Inference**: Scholarships are categorized by inferred fields/levels
5. **Results Display**: Paginated results with sorting options

---

## API Endpoints

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/login` | GET/POST | User login page and authentication |
| `/register` | GET/POST | User registration |
| `/logout` | GET | Logout current user |

### Pages
| Endpoint | Description | Auth Required |
|----------|-------------|---------------|
| `/` | Landing page | No |
| `/search.html` | Scholarship search | No |
| `/ai-recommend.html` | AI advisor chat | Yes |
| `/bookmarks.html` | Saved scholarships | Yes |
| `/admin` | Admin dashboard | Admin only |

### API Routes
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ai/chat` | POST | AI advisor conversation endpoint |
| `/api/search` | GET | Scholarship search with filters |
| `/api/scholarship/<id>` | GET | Get detailed scholarship info |
| `/api/stats` | GET | Application statistics |
| `/health` | GET | Health check endpoint |

---

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TOGETHER_API_KEY` | Together AI API key for LLM | Yes |
| `FLASK_SECRET_KEY` | Secret key for Flask sessions | Yes |
| `FLASK_DEBUG` | Enable debug mode (True/False) | No (default: True) |
| `FLASK_RUN_HOST` | Host to bind to | No (default: 0.0.0.0) |
| `FLASK_RUN_PORT` | Port to run on | No (default: 5000) |

### AI Configuration

Edit `ai_advisor.py` to customize:

```python
# Embedding model
RAG_EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# LLM Configuration
RAG_LLM_API_BASE = "https://api.together.xyz/v1"
RAG_LLM_MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"

# Knowledge base directory
RAG_DATA_DIR_NAME = "data"
```

### Database Configuration

The application uses two SQLite databases:
- **scholarships.db**: Contains all scholarship data (pre-populated)
- **users.db**: Contains user accounts and bookmarks (auto-created)

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Ensure all dependencies are installed in virtual environment |
| AI advisor not responding | Check `TOGETHER_API_KEY` is set correctly |
| "RAG system not initialized" | Verify `data/` directory contains JSON files |
| Database errors | Check that `scholarships.db` exists and is readable |
| Login not working | Verify `users.db` has been created and is writable |

### Debug Mode

Enable Flask debug mode for detailed error messages:

```bash
$env:FLASK_DEBUG = "True"
python app.py
```

### Health Check

Visit `/health` endpoint to verify all systems are operational:

```json
{
  "status": "healthy",
  "dependencies": {
    "scholarships_database": {"status": "ok"},
    "users_database": {"status": "ok"},
    "rag_system": {"status": "ok"}
  }
}
```

---

## Development

### Adding New Scholarships

1. Add scholarship data to `scholarships.db` (SQLite)
2. Add corresponding JSON documents to `data/` directory for RAG
3. Restart the application to rebuild the vector index

### Modifying AI Behavior

Edit the system prompt in `ai_advisor.py`:

```python
system_prompt = (
    "You are ScholarshipGPT, an efficient AI scholarship advisor..."
    # Customize response guidelines and recommendation triggers
)
```

### Database Schema

**scholarships table:**
- `id` (INTEGER PRIMARY KEY)
- `title` (TEXT)
- `award_amount` (TEXT)
- `deadline` (TEXT)
- `eligibility_summary_text` (TEXT)
- `application_link` (TEXT)
- `requirements_structured_json` (JSON)
- `keywords_json` (JSON)

**users table:**
- `id` (INTEGER PRIMARY KEY)
- `name` (TEXT)
- `email` (TEXT UNIQUE)
- `password_hash` (TEXT)
- `created_at` (TIMESTAMP)

---

## Security Considerations

- **API Keys**: Never commit API keys to version control; always use environment variables
- **Passwords**: All passwords are hashed using Werkzeug's security functions
- **Sessions**: Flask secret key should be strong and unique for production
- **Admin Access**: Admin page is restricted to specific email address (`ADMIN_EMAIL` in app.py)

---

## Contributing

Contributions are welcome. Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License.

---

## Acknowledgments

- [LlamaIndex](https://www.llamaindex.ai/) for RAG infrastructure
- [Together AI](https://www.together.ai/) for LLM API access
- [HuggingFace](https://huggingface.co/) for embedding models
- [Flask](https://flask.palletsprojects.com/) for the web framework

---

## Contact

For questions or support, please open an issue on GitHub.

---

**Helping students fund their education through intelligent technology**

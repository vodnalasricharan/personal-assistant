# 🤖 Personal AI Assistant

A production-quality **Personal AI Agent** that represents you to the world.

Visitors can ask questions about your background, skills, projects, and experience. The agent answers using **RAG over your personal knowledge base**, and can also perform actions like sending emails, generating presentations, creating resumes, and producing documents — all via an intelligent LangGraph-powered agent loop.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **RAG Knowledge Base** | Semantic search over your PDF, DOCX, TXT, Markdown, JSON, CSV files |
| 🤖 **Gemini LLM** | Powered by Google Gemini for both chat and embeddings |
| 🧠 **Intent-Routing Agent** | LangGraph-style agent that classifies intent and routes to the right tool |
| 📧 **Email Tool** | Drafts and sends Gmail emails with explicit user confirmation |
| 📊 **PPT Generator** | Creates polished `.pptx` presentations from your knowledge base |
| 📄 **Resume Generator** | Generates tailored DOCX resumes for any role |
| 📝 **Document Generator** | Creates DOCX/PDF bios, profiles, and project portfolios |
| 💬 **Conversation Memory** | SQLite-backed persistent chat history |
| 📚 **Knowledge Base UI** | Upload, inspect, and manage indexed documents |
| 📄 **Generated Files UI** | Download all generated files |
| ⚙️ **Settings UI** | View configuration status |
| 🛡️ **Security** | No hardcoded secrets; email requires explicit confirmation |

---

## 🏗️ Architecture

```
User
  │
  ▼
Streamlit UI
  │
  ▼
LangGraph Agent (graph.py)
  │
  ├── Classify Intent (nodes.py)
  │
  ├── Retrieve (RAG → ChromaDB)
  │
  └── Route to node:
       ├── knowledge_query    → generate_response (Gemini + RAG context)
       ├── hiring_contact     → draft_email → [user confirmation] → send_email
       ├── generate_presentation → plan_presentation → build_presentation (python-pptx)
       ├── generate_resume    → plan_resume → build_resume_docx (python-docx)
       ├── generate_document  → plan_document → build_docx / build_pdf
       └── general_conversation → generate_response (Gemini)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | Streamlit |
| LLM | Google Gemini (`gemini-3.1-flash-lite` by default) |
| Embeddings | Gemini `gemini-embedding-2` |
| Agent | LangGraph-style directed graph (implemented in pure Python) |
| Vector DB | ChromaDB (local, persistent) |
| Memory | SQLite |
| PPT | python-pptx |
| DOCX | python-docx |
| PDF | ReportLab |
| PDF loading | pypdf |
| Email | Gmail SMTP (smtplib) |
| Observability | JSON file logging + optional LangSmith tracing |
| Config | Pydantic Settings |
| Tests | pytest |

---

## 📁 Project Structure

```
personal-ai-assistant/
│
├── app.py                  ← Streamlit entry point
├── requirements.txt
├── .env.example
│
├── config/
│   ├── settings.py         ← Pydantic settings (env vars)
│   ├── logging.py          ← JSON rotating log handler
│   └── langsmith.py        ← Optional LangSmith tracing helpers
│
├── agent/
│   ├── graph.py            ← AgentGraph (intent routing pipeline)
│   ├── nodes.py            ← Individual agent nodes
│   ├── state.py            ← AgentState dataclass
│   └── prompts.py          ← All LLM prompts
│
├── rag/
│   ├── ingestion.py        ← Document loading + chunking pipeline
│   ├── chunking.py         ← Text splitter with overlap
│   ├── embeddings.py       ← Gemini + hash embedding providers
│   ├── vector_store.py     ← ChromaDB wrapper
│   ├── retriever.py        ← High-level retrieval API
│   └── types.py            ← DocumentChunk, RetrievedChunk, RetrievalResult
│
├── tools/
│   ├── rag_tool.py
│   ├── email_tool.py
│   ├── ppt_tool.py
│   ├── resume_tool.py
│   ├── document_tool.py
│   └── web_search_tool.py  ← Disabled by default
│
├── generators/
│   ├── ppt.py              ← python-pptx presentation builder
│   ├── resume.py           ← DOCX resume generator
│   ├── docx.py             ← Generic DOCX generator
│   └── pdf.py              ← ReportLab PDF generator
│
├── memory/
│   ├── database.py         ← SQLite DDL + connection helpers
│   └── conversation.py     ← ConversationMemory class
│
├── ui/
│   ├── chat.py             ← Chat page (messages, sources, downloads)
│   ├── knowledge_base.py   ← Upload / manage / inspect KB
│   ├── generated_files.py  ← List and download generated files
│   └── settings.py         ← Settings display + About page
│
├── data/                   ← ← Put your personal documents HERE
│   └── README.md
│
├── generated/              ← Generated files are saved here
├── db/                     ← ChromaDB + SQLite live here
├── logs/                   ← Rotating JSON logs
└── tests/
    ├── test_rag.py
    ├── test_agent.py
    ├── test_generators.py
    └── test_memory.py
```

---

## 🚀 Installation

### Prerequisites
- Python 3.11+
- A Google Gemini API key (free tier available at https://aistudio.google.com/)
- (Optional) Gmail account with App Password for email functionality

### Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd personal-ai-assistant

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add at minimum: GEMINI_API_KEY=your_key_here

# 5. Run the app
streamlit run app.py
```

The app will open at http://localhost:8501.

---

## 🔧 Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional — enable email functionality
CONTACT_EMAIL=you@example.com
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password

# Storage (defaults work for local development)
CHROMA_PERSIST_DIRECTORY=./db/chroma
SQLITE_DATABASE=./db/app.db

# RAG tuning
TOP_K=5
CHUNK_SIZE=800
CHUNK_OVERLAP=100

# Optional LangSmith tracing
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=personal-ai-assistant
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

### Gmail App Password setup
1. Enable 2-Factor Authentication on your Google account.
2. Go to https://myaccount.google.com/apppasswords
3. Generate an App Password for "Mail".
4. Use that 16-character password as `GMAIL_APP_PASSWORD`.

---

## 📚 How to Add Your Personal Information

1. **Create your documents** in the `data/` directory:
   ```
   data/
   ├── about_me.md
   ├── resume.pdf   (or resume.docx)
   ├── experience.md
   ├── education.md
   ├── skills.md
   ├── projects/
   │   ├── project1.md
   │   └── project2.md
   └── achievements.md
   ```

2. **Ingest them** via one of:
   - Streamlit UI → **Knowledge Base** → **Run bulk ingest**
   - Upload individual files directly from the Knowledge Base page

3. **Start chatting** — the assistant will use your documents to answer questions.

---

## 🔍 How RAG Works

```
User question
    │
    ▼
Gemini embeddings → query vector
    │
    ▼
ChromaDB cosine similarity search → top-k chunks
    │
    ▼
Deduplicate chunks
    │
    ▼
Build context + cite sources
    │
    ▼
Gemini LLM → grounded answer with source citations
```

- **Chunk size**: 800 characters by default (configurable)
- **Overlap**: 100 characters (configurable)
- **Top-k**: 5 results per query (configurable)
- **Deduplication**: exact-match normalized text deduplication before LLM call

---

## 🧠 How the Agent Works

The agent follows a **directed graph** of nodes:

1. **Classify intent** → which action does the user want?
2. **Retrieve** (if personal knowledge needed) → RAG
3. **Route** to the appropriate specialist node:
   - `knowledge_query` → RAG + Gemini response
   - `hiring_contact` → RAG + email draft → user confirmation → send
   - `generate_presentation` → RAG + PPT plan + python-pptx
   - `generate_resume` → RAG + resume plan + python-docx
   - `generate_document` → RAG + document content + DOCX/PDF
   - `general_conversation` → Gemini chat

The agent **never fabricates personal information** — it only uses retrieved chunks.

### Optional LangSmith tracing

If you want hosted trace visibility in addition to local JSON logs, enable LangSmith in [`.env.example`](.env.example):

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=personal-ai-assistant
```

When enabled, the app traces:
- [`AgentGraph.run()`](agent/graph.py:49)
- [`node_classify_intent()`](agent/nodes.py:90)
- [`node_retrieve()`](agent/nodes.py:118)
- [`node_generate_response()`](agent/nodes.py:176)

Local logging to [`logs/app.log`](logs/app.log) remains enabled regardless.

---

## 📧 How Email Works

1. User says something like "I want to hire him" or "Can I contact you?"
2. Agent detects `hiring_contact` intent.
3. RAG retrieves relevant background.
4. Gemini drafts a professional email.
5. Streamlit shows a **confirmation UI** with the draft.
6. User clicks **Send Email** (or Cancel).
7. Email is sent via Gmail SMTP **only after explicit confirmation**.

---

## 📊 How PPT Generation Works

1. User requests a presentation.
2. RAG retrieves all relevant knowledge.
3. Gemini creates a structured slide plan (JSON).
4. `generators/ppt.py` renders slides using python-pptx.
5. File is saved to `generated/`.
6. Streamlit shows a download button.

---

## 🧪 Testing

```bash
# Run all tests (no API key needed — uses local embeddings + mocked LLM)
pytest tests/ -v

# Run a specific test file
pytest tests/test_rag.py -v
pytest tests/test_memory.py -v
pytest tests/test_generators.py -v
pytest tests/test_agent.py -v
```

Tests use:
- `HashEmbeddingProvider` (deterministic local embeddings — no Gemini API needed)
- `unittest.mock.patch` for Gemini LLM calls
- `tmp_path` pytest fixture for isolated file system

---

## 🔒 Security

| Concern | Mitigation |
|---------|-----------|
| API keys | Loaded from `.env` only; never hardcoded |
| `.env` in git | Excluded by `.gitignore` |
| Email | Requires explicit user confirmation in UI |
| File uploads | Extension and size validated |
| Path traversal | Uploads saved to controlled directory only |
| Arbitrary code | User prompts cannot execute Python code |
| Secrets in logs | Credentials are never logged |
| Stack traces | UI shows friendly messages only |

---

## 🐛 Troubleshooting

| Problem | Fix |
|---------|-----|
| `GEMINI_API_KEY not set` | Add key to `.env` |
| `ChromaDB error` | Delete `db/chroma/` and re-ingest |
| `Email not sending` | Check Gmail App Password; enable 2FA first |
| `No results from RAG` | Ingest documents first via Knowledge Base page |
| `PPT/DOCX download empty` | Check `generated/` directory; look at logs |
| `Import error` | Run `pip install -r requirements.txt` in your venv |
| `LangSmith traces not appearing` | Set `LANGSMITH_TRACING=true`, add `LANGSMITH_API_KEY`, restart Streamlit |

Detailed errors are logged to `logs/app.log` in JSON format.

---

## 🚢 Deployment Notes

The app is designed for local-first use but can be deployed to any platform that supports Python + persistent storage:

- **Streamlit Community Cloud**: Works if you set secrets via the dashboard.
- **Fly.io / Railway / Render**: Mount a persistent volume for `db/` and `generated/`.
- **Docker**: Use `COPY data/ /app/data/` and set env vars via Docker secrets.
- **ChromaDB**: Currently uses local persistence; migrate to a remote Chroma server for multi-instance deployments.

---

## 📝 License

MIT — use freely for personal and commercial projects.

---

*Built with Python 3.11 · Streamlit · Google Gemini · ChromaDB · LangGraph*

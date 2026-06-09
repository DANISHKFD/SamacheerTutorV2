# 🎓 Vidya — AI Tutor for Tamil Nadu State Board Students (Classes 8–10)

A full-stack RAG-powered chatbot that answers questions from Maths, Science, and Social Science using Samacheer Kalvi textbook content. Built with Flask + FAISS + Sentence Transformers + Google Gemini.

---

## 📁 Project Structure

```
ai-tutor/
│
├── backend/                         # Python Flask backend
│   ├── app.py                       # Flask app entry point
│   ├── config.py                    # Config (reads .env)
│   ├── requirements.txt             # Python dependencies
│   ├── .env.example                 # Copy to .env and add your key
│   │
│   ├── routes/
│   │   └── chat.py                  # /api/chat and /api/simplify endpoints
│   │
│   ├── services/
│   │   ├── rag.py                   # FAISS index build + search
│   │   ├── embedding.py             # Sentence-transformers embeddings
│   │   ├── ai_client.py             # Gemini API wrapper
│   │   └── prompt_engine.py         # Subject-aware prompt builder
│   │
│   └── utils/
│       ├── chunker.py               # Text splitting into chunks
│       └── text_cleaner.py          # Raw text cleaning
│
├── frontend/                        # Vanilla HTML/CSS/JS frontend
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── scripts/
│   ├── prepare_data.py              # Clean + chunk textbook .txt files
│   └── build_index.py               # Build FAISS index from chunks
│
├── data/                            # Raw textbook text files (add content here)
│   ├── maths.txt
│   ├── science.txt
│   └── social.txt
│
└── README.md
```

---

## ⚙️ Setup Instructions (Step by Step)

### Step 1: Clone / Download the project

```bash
cd ai-tutor
```

### Step 2: Set up Python environment

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r backend/requirements.txt
```

> ⚠️ First install downloads the `all-MiniLM-L6-v2` model (~80MB). This only happens once.

### Step 4: Add your Gemini API key

```bash
# Copy the example file
cp backend/.env.example backend/.env

# Open backend/.env and replace with your actual key:
# GEMINI_API_KEY=AIza...your_key_here
```

Get a free Gemini API key at: https://aistudio.google.com/app/apikey

### Step 5: Add textbook content

Edit or replace these files with real Samacheer Kalvi content:
- `data/maths.txt`
- `data/science.txt`
- `data/social.txt`

Sample content is already included so you can test immediately.

### Step 6: Process the textbook data

```bash
python scripts/prepare_data.py
```

This cleans the text and splits it into chunks, saving `data/chunks.json`.

### Step 7: Build the FAISS index

```bash
python scripts/build_index.py
```

This creates the vector embeddings and saves the FAISS index to `backend/index/`.

### Step 8: Start the Flask backend

```bash
python backend/app.py
```

You should see: `🚀 AI Tutor backend started at http://127.0.0.1:5000`

### Step 9: Open the frontend

Open `frontend/index.html` in your browser (double-click or use Live Server in VS Code).

---

## 🔁 How RAG Works

```
Student Question
      ↓
  Embed question (sentence-transformers)
      ↓
  Search FAISS index → top 3 relevant textbook chunks
      ↓
  Build prompt (subject-specific rules + context + question)
      ↓
  Send to Gemini API
      ↓
  Return clean answer to student
```

---

## 💡 Features

| Feature | Description |
|---------|-------------|
| 📚 Subject-aware answers | Different prompt strategies for Maths, Science, Social |
| 💬 Simple / Detailed mode | Student can choose explanation depth |
| ✨ Explain Simpler | One-click to re-explain in even simpler language |
| ⚡ Quick Topics | Pre-loaded starter questions |
| 📱 Responsive UI | Works on mobile and desktop |
| 🔍 RAG | Answers grounded in actual textbook content |

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, Flask |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) — **FREE, local** |
| Vector DB | FAISS (faiss-cpu) |
| LLM | Google Gemini 1.5 Flash |
| Frontend | Vanilla HTML5, CSS3, JavaScript |

---

## 📝 API Reference

### POST /api/chat
```json
// Request
{
  "question": "What is photosynthesis?",
  "subject": "science",
  "mode": "easy"
}

// Response
{
  "answer": "Photosynthesis is the process by which...",
  "chunks_used": ["Photosynthesis is the process...", "..."]
}
```

### POST /api/simplify
```json
// Request
{
  "text": "Previous AI answer to simplify...",
  "subject": "science"
}

// Response
{
  "answer": "Simpler version of the answer..."
}
```

---

## 🔧 Troubleshooting

**"FAISS index not found"** → Run `python scripts/build_index.py` first.

**"GEMINI_API_KEY is not set"** → Create `backend/.env` from `.env.example` and add your key.

**"Could not connect to backend"** → Make sure `python backend/app.py` is running on port 5000.

**Slow first response** → The embedding model loads on first use. Subsequent responses are faster.

---

## 📖 Adding More Textbook Content

Simply append more text to `data/maths.txt`, `data/science.txt`, or `data/social.txt`, then re-run:

```bash
python scripts/prepare_data.py
python scripts/build_index.py
```

The backend will automatically use the updated index on next restart.

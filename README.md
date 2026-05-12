# AI Drive File Discovery Agent

A conversational AI-powered Google Drive search assistant built using FastAPI, LangChain, Groq LLMs, and Streamlit.

The assistant allows users to search, filter, and discover files inside a designated Google Drive folder using natural language queries.

---

## Features

- Conversational AI chatbot
- Google Drive file discovery
- Natural language search
- Dynamic Google Drive q query generation
- Search by:
  - exact filename
  - partial filename
  - mimeType
  - fullText
  - modified date
- Streamlit chat interface
- FastAPI backend
- LangChain tool-calling agent
- Groq/OpenAI/Gemini provider support

---

## Tech Stack

### Backend
- FastAPI
- LangChain
- Google Drive API

### Frontend
- Streamlit

### LLM
- Groq Llama 3.3 70B

---

## Project Structure

```bash
project/
│
├── backend/
│   ├── main.py
│   ├── agent.py
│   ├── drive_tool.py
│   ├── config.py
│
├── frontend/
│   ├── app.py
│
├── service-account.json
├── .env
├── requirements.txt
```

---

## Setup

### 1. Clone repository

```bash
git clone <repo-url>
cd ai-drive-file-discovery-agent
```

---

### 2. Create virtual environment

```bash
python -m venv venv
```

Activate:

```bash
venv\Scripts\activate
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Configure environment variables

Create `.env` file:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_api_key

GOOGLE_APPLICATION_CREDENTIALS=service-account.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id

API_BASE_URL=http://localhost:8000
```

---

### 5. Run backend

```bash
uvicorn backend.main:app --reload
```

---

### 6. Run frontend

```bash
streamlit run frontend/app.py
```

---

## Example Queries

- Find pdf files
- Show images
- Find invoice documents
- Find recent reports
- Find files modified last week

---

## Deployment

- Backend: Render
- Frontend: Streamlit Community Cloud

---

## Author

Prayag Singh

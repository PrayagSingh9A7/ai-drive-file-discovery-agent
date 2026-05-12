# AI-Powered Google Drive File Discovery Assistant

A production-ready FastAPI + Streamlit application that uses LangChain and an LLM to translate natural-language chat requests into Google Drive API `q` queries. Searches are restricted to one configured Google Drive folder through a service account.

## Features

- Conversational Streamlit chat UI with chat history and result cards
- FastAPI backend with `POST /chat`
- LangChain tool-calling agent with a custom `DriveSearchTool`
- Gemini by default, configurable for OpenAI or Groq
- Google Drive `files.list()` integration with pagination
- Searches restricted to `GOOGLE_DRIVE_FOLDER_ID`
- Supports `name contains`, exact `name =`, `mimeType`, `fullText`, and `modifiedTime` filters
- Service account authentication
- Deployment-ready for Render and Railway

## Project Structure

```text
project/
|-- backend/
|   |-- __init__.py
|   |-- main.py
|   |-- agent.py
|   |-- drive_tool.py
|   |-- config.py
|   `-- requirements.txt
|-- frontend/
|   `-- app.py
|-- requirements.txt
|-- .env.example
`-- README.md
```

## Setup

1. Create and activate a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Create your local environment file.

```bash
cp .env.example .env
```

Fill in:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
GOOGLE_DRIVE_FOLDER_ID=your-folder-id
```

## Google Cloud Setup

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Enable the **Google Drive API**.
4. Go to **IAM & Admin > Service Accounts**.
5. Create a service account, then create a JSON key.
6. Store the JSON key somewhere safe and set `GOOGLE_APPLICATION_CREDENTIALS` to its absolute path.

## Share the Drive Folder

1. Open the Google Drive folder that the assistant should search.
2. Click **Share**.
3. Add the service account email, usually ending in `iam.gserviceaccount.com`.
4. Give it **Viewer** permission.
5. Copy the folder ID from the URL:

```text
https://drive.google.com/drive/folders/FOLDER_ID_HERE
```

Set that value as `GOOGLE_DRIVE_FOLDER_ID`.

## Run Locally

Start the backend:

```bash
uvicorn backend.main:app --reload
```

Start the frontend in another terminal:

```bash
streamlit run frontend/app.py
```

Open the Streamlit URL, usually `http://localhost:8501`.

## Example Requests

```text
Find pdf reports from last week
Show images related to invoices
Find my finance sheet
Only the recent ones
Search text files mentioning onboarding
Find the exact file named Quarterly Report.pdf
```

The LLM dynamically generates Google Drive query fragments. The backend tool adds:

```text
'<GOOGLE_DRIVE_FOLDER_ID>' in parents and trashed = false
```

## API

### `POST /chat`

Request:

```json
{
  "message": "Find pdf reports from last week",
  "session_id": "user-session-1"
}
```

Response:

```json
{
  "answer": "I found 3 PDF report files modified recently.",
  "files": [
    {
      "id": "abc123",
      "name": "Weekly Report.pdf",
      "mimeType": "application/pdf",
      "modifiedTime": "2026-05-08 10:15 UTC",
      "webViewLink": "https://drive.google.com/file/...",
      "webContentLink": "https://drive.google.com/uc?..."
    }
  ],
  "generated_query": "'folder-id' in parents and trashed = false and (mimeType='application/pdf' and name contains 'report')"
}
```

## Deployment: Render

Backend web service:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Add environment variables from `.env.example`
- For service account JSON, either use a Render secret file or store JSON in a secret and write it during startup.

Frontend web service:

- Build command: `pip install -r requirements.txt`
- Start command: `streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0`
- Set `API_BASE_URL` to the deployed backend URL.

## Deployment: Railway

Backend:

```bash
railway up
```

Set the start command:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Frontend:

```bash
streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0
```

Set `API_BASE_URL` to the backend service URL and configure all LLM and Google Drive variables.

## Notes for Production

- Use a persistent store such as Redis or Postgres for conversation memory across backend restarts.
- Keep service account keys in secret managers, not in the repository.
- Restrict CORS to your deployed frontend domain.
- Tune `DRIVE_PAGE_SIZE` and `DRIVE_MAX_PAGES` for larger folders.
- Consider audit logging for file discovery activity in regulated environments.

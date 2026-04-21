# Food Safety RAG Pipeline

This project builds a robust Retrieval-Augmented Generation (RAG) system dedicated to food safety materials. It pulls raw domain knowledge directly from Google Drive, processes it, and embeds it into a vector database (Pinecone) to be referenced by Large Language Models (Gemini, Groq) to accurately answer queries.

## Project Structure

* `/config`: Central configuration manager. Loads environment variables dynamically using `python-dotenv`.
* `/data/raw`: Houses the master `drive_files.json` which maps categories to Google Drive Folder URLs. When the download script runs, nested files are securely synchronized here.
* `/scripts`: Dedicated scripts like `download_drive.py` used to incrementally parse, authenticate, and batch-download raw PDFs to your local machine.
* `/services`: Service singletons that manage database connects and ML integrations such as Gemini (for embeddings), Groq (for fast inference), and Pinecone (as the semantic VectorDB).
* `/test`: Simple integration tests to visually verify that services route effectively and authentication tokens are working.

## Setup Requirements

### 1. Environment Configurations

All system credentials should be safely stored in the `.env` file at the root of your project directory. 
Create `.env` using following properties and insert your actual keys:

```bash
PINECONE_API_KEY=
PINECONE_ENVIRONMENT=
PINECONE_INDEX_NAME=
GEMINI_API_KEY=
GROQ_API_KEY=
```

### 2. Google Drive Authentication

Before you can download knowledge from Drive, you must ensure that you have standard OAuth Client credentials capable of local authentication.
1. Place your OAuth credentials inside `credentials.json` at the project root.
2. Ensure your `credentials.json` states that your `redirect_uris` includes `http://localhost:8080/`.

### 3. Downloading Raw Data

To pull all relevant documents from Google Drive to your local machine:
1. Ensure your Python virtual environment is activated and your `requirements.txt` dependencies are installed.
2. Run the executable script from the root directory:
   
   ```bash
   python scripts/download_drive.py
   ```

3. A local authentication window will open. Selecting offline access ensures a `token.json` file is cached at your root directory. The script uses this token to perpetually refresh during background downloads without timing out.
4. The downloaded materials will be automatically routed into human-readable subdirectories directly inside `/data/raw`. The script utilizes recursive folder checking—if network connection drops, just rerun the command; it intelligently skips documents already saved.

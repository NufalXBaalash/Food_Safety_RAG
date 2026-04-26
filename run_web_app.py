import uvicorn
import os

if __name__ == "__main__":
    print("Starting Food Safety RAG Web Portal...")
    print("URL: http://localhost:8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

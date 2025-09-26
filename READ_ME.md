# ChatGPT Automation 🚀

This project is a **FastAPI service** that uses **SeleniumBase + headless Chrome** to automate tasks.  
It runs locally with Docker and can be deployed to **Google Cloud Run**.

---

## Run Locally

1. Clone repo:
   ```bash
   git clone https://github.com/<your-username>/<your-repo>.git
   cd <your-repo>
2.Install dependencies (optional, for local dev):
pip install -r requirements.txt

3.Run:
uvicorn main:app --reload --host 0.0.0.0 --port 8000

4.Run with Docker
# build image
docker build -t chatgpt-automation .

# run container
docker run -p 8000:8000 chatgpt-automation

Deploy to Google Cloud Run
# build image with Artifact Registry tag
docker build -t asia-south1-docker.pkg.dev/<PROJECT-ID>/<REPO>/chatgpt-automation .

# push image
docker push asia-south1-docker.pkg.dev/<PROJECT-ID>/<REPO>/chatgpt-automation

# deploy to Cloud Run
gcloud run deploy chatgpt-automation \
  --image asia-south1-docker.pkg.dev/<PROJECT-ID>/<REPO>/chatgpt-automation \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated

EXAMPLE CURL COMMANDS

curl -X POST "https://chatgpt-automation-904935460967.europe-west1.run.app/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  -d '{
    "prompt": "Write me a short motivational quote"
  }'

curl -X GET "https://chatgpt-automation-904935460967.europe-west1.run.app/health"

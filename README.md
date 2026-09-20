# Job Hunt Copilot

An AI-powered job search assistant that turns your resume into a targeted job search and personalized recruiter outreach.

**Live demo:** [job-hunt-copilot-nine.vercel.app](https://job-hunt-copilot-nine.vercel.app/)

---

## What it does

Job hunting involves a lot of repetitive work: figuring out which titles to search for, running the same search across multiple roles and locations, and writing outreach emails one at a time. This app handles all three from a single resume upload.

1. **Upload a resume** — the app parses the PDF, verifies it's actually a resume, and uses the Gemini API to infer your experience level and suggest job titles worth targeting.
2. **Search across roles and locations** — queries SerpApi for every role/location combination at once and returns a consolidated feed, with a remote-only filter.
3. **Generate outreach** — for any job in the results, generates a personalized recruiter email grounded in both the job description and your resume.

---

## Screenshots

<!-- TODO: add 2–3 screenshots or a short GIF of the flow.
     Put them in a /screenshots folder and reference them like:
     ![Resume upload](screenshots/upload.png) -->

---

## Tech stack

| Layer | Stack |
|---|---|
| Frontend | React (Vite) |
| Backend | FastAPI (Python) |
| AI | Google Gemini API |
| Job data | SerpApi (Google Jobs) |
| PDF parsing | <!-- TODO: PyPDF2 / pdfplumber / whichever you used --> |
| Deployment | Vercel |

---

## Architecture

```
job-hunt-copilot/
├── frontend/           # React + Vite client
├── main.py             # FastAPI app — API routes
└── requirements.txt    # Python dependencies
```

The React client talks to the FastAPI backend over REST. All third-party API keys (Gemini, SerpApi) are held server-side and never exposed to the browser.

### API endpoints

<!-- TODO: fill in your actual routes and payloads. Example format: -->

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/upload-resume` | Parse and validate a resume PDF, return suggested job titles |
| `POST` | `/search-jobs` | Fetch jobs for the given roles and locations |
| `POST` | `/generate-email` | Generate a recruiter email from a resume and job description |

---

## Running locally

### Prerequisites
- Python 3.10+
- Node.js 18+
- A Google Gemini API key
- A SerpApi key

### Backend

```bash
git clone https://github.com/Ashtha613/job-hunt-copilot.git
cd job-hunt-copilot

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_key_here
SERPAPI_API_KEY=your_serpapi_key_here
```

Start the server:

```bash
uvicorn main:app --reload
```

The API runs at `http://localhost:8000`. Interactive docs are available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The client runs at `http://localhost:5173`.

---

## Design notes

- **FastAPI** was chosen for its native async support, automatic OpenAPI documentation, and Pydantic-based request validation.
- **Resume validation** happens before any AI call — non-resume PDFs are rejected early rather than being sent to the model, which avoids wasted API quota and nonsensical output.
- **Keys stay server-side.** The frontend never holds an API key; all third-party calls are proxied through the backend.

---

## Roadmap

- [ ] Persist search history and saved jobs
- [ ] Support DOCX resumes alongside PDF
- [ ] Batch email generation across multiple listings
- [ ] Application tracking

---

## Author

**Ashtha Kumari**

[GitHub](https://github.com/Ashtha613)

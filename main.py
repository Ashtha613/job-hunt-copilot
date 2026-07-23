from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import PyPDF2
import io
import asyncio
import httpx
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = genai.GenerativeModel('gemini-3.5-flash')

class UnifiedEmailRequest(BaseModel):
    job_description: str
    resume_text: str
    company_name: str
    role_title: str

@app.get("/")
def read_root():
    return {"message": "Hello from the Job Hunt Copilot Backend!"}

# --- NODE 0 (THE PROFILER) ---
@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    print("🚦 1. File received by backend!")
    
    try:
        contents = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(contents))
        
        resume_text = "".join(page.extract_text() or "" for page in pdf_reader.pages)

        print("🚦 2. PDF read successfully! Sending to AI...")
        
        # REVERTED PROMPT: Back to your original, proven logic
        prompt = f"""
        You are an expert technical recruiter. Analyze the following resume text and first determine the candidate's exact years of experience and career level (e.g., Entry-level, Junior, Mid-level, Senior). 
        
        Based strictly on their actual demonstrated experience, suggest 5 realistic job titles they are currently eligible for. 
        - Do NOT suggest "Senior", "Lead", "Principal", or "Manager" roles unless the resume clearly shows 5+ years of relevant experience.
        - If they are a student, recent graduate, or have under 2 years of experience, only suggest "Junior", "Entry-level", or standard roles (e.g., "Software Engineer" rather than "Senior Software Engineer").
        
        Respond ONLY with a raw JSON array of strings. Do not include markdown, backticks, or any conversational text.
        Example output: ["Junior Frontend Developer", "React Developer", "Web Developer"]
        
        Resume text:
        {resume_text}
        """
        
        response = model.generate_content(prompt)
        print("🚦 3. AI finished generating!")
        
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        suggested_roles = json.loads(cleaned_response)
        
        print("🚦 4. Ready to send back to frontend!")
        return {
            "raw_text": resume_text,
            "suggested_roles": suggested_roles
        }
        
    except Exception as e:
        print(f"❌ Error during resume processing: {e}")
        return {"error": str(e)}

# --- NODE 1 (THE SCOUT) ---
async def fetch_jobs(search_query: str, is_remote: bool):
    params = {
        "engine": "google_jobs",
        "q": search_query,
        "hl": "en",
        "api_key": os.getenv("SERPAPI_KEY"),
    }
    
    if is_remote:
        params["ltype"] = "1"
        
    async with httpx.AsyncClient() as client:
        response = await client.get("https://serpapi.com/search", params=params)
        return response.json()

@app.get("/search-jobs")
async def search_jobs(role: str, location: str):
    target_roles = role.split(" OR ")
    
    if " in " in location:
        work_model, loc_str = location.split(" in ", 1)
        target_locations = loc_str.split(" OR ")
    else:
        work_model = location
        target_locations = [""]

    tasks = []
    is_remote = (work_model == "Remote")
    
    for single_role in target_roles:
        for single_loc in target_locations:
            
            query = single_role
            
            if "junior" in single_role.lower() or "entry" in single_role.lower() or "intern" in single_role.lower():
                query += " -senior -lead -principal -manager -director"
            
            # BUG FIX: This now ensures your location (like "India") is always attached to the query, even if it is a Remote role.
            if single_loc:
                query += f" in {single_loc}"
                
            tasks.append(fetch_jobs(query, is_remote))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_jobs = []
    seen_jobs = set()
    
    for data in results:
        if isinstance(data, dict) and "jobs_results" in data:
            for job in data["jobs_results"][:10]: 
                title = job.get("title", "")
                company = job.get("company_name", "")
                
                unique_id = f"{title}-{company}"
                
                if unique_id not in seen_jobs:
                    seen_jobs.add(unique_id)
                    
                    apply_link = job.get("share_link", "#")
                    if "apply_options" in job and len(job["apply_options"]) > 0:
                        apply_link = job["apply_options"][0].get("link", apply_link)

                    all_jobs.append({
                        "title": title,
                        "company": company,
                        "description": job.get("description", "")[:300] + "...",
                        "apply_link": apply_link
                    })
                    
    return {"jobs_found": all_jobs}

# --- NODE 2 (THE OUTREACH AGENT) ---
@app.post("/generate-outreach")
def generate_outreach(data: UnifiedEmailRequest):
    prompt = f"""
    You are an elite Career Coach and Technical Recruiter. 
    Perform the following workflow based on the provided Job Description and Resume:
    
    1. Identify the top 3-4 core technical skills required for the role.
    2. Mentally cross-reference these skills with the candidate's actual experience in the Resume.
    3. Draft a highly professional, confident, and polite cold outreach email (under 150 words) to a recruiter at {data.company_name} for the {data.role_title} role.
    4. In the email, explicitly highlight 1-2 projects/points from the resume that perfectly align with those core skills.
    
    Job Description:
    {data.job_description}
    
    Resume Text:
    {data.resume_text}
    
    Output ONLY the final email text. Use a placeholder for the user's signature.
    """
    response = model.generate_content(prompt)
    return {"cold_email": response.text.strip()}
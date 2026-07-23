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
    allow_origins=["*"], # Allows any frontend to connect (good for local testing and Vercel)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Using your designated Gemini model
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
        # 1. Read the PDF file in memory
        contents = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(contents))
        
        resume_text = "".join(page.extract_text() or "" for page in pdf_reader.pages)

        print("🚦 2. PDF read successfully! Sending to AI...")
        
        # 2. Ask Gemini to analyze the resume using the holistic leveling prompt
        prompt = f"""
        You are an elite Technical Recruiter and Career Placement Specialist. Your task is to perform a deep, holistic analysis of the provided resume and suggest 5 highly realistic job titles the candidate should apply for right now.

        You must analyze EVERYTHING: total years of professional employment, internships, personal projects, education timeline, and the actual complexity of their work. Do not over-level or under-level the candidate.

        Follow these strict leveling guidelines based on your analysis of their timeline:
        - 0 Years / Only Projects / Student / Bootcamper: You MUST prefix roles with "Entry-Level", "Junior", "Intern", or "Trainee" (e.g., "Entry-Level Frontend Developer").
        - 1 to 2 Years of Professional Experience: Suggest "Junior" or "Associate" level roles (e.g., "Junior Software Engineer").
        - 3 to 5 Years of Experience: Suggest mid-level, standard titles without prefixes (e.g., "Data Analyst", "Backend Engineer").
        - 5+ Years of Experience: Suggest "Senior", "Lead", or "Principal" roles ONLY IF the resume explicitly demonstrates leadership, architectural design, or high-level business impact.

        Match the job titles specifically to the technologies, industries, and exact skills highlighted in the resume. 

        Respond ONLY with a raw JSON array of 5 strings. Do not include markdown formatting, backticks, or conversational text.
        Example output: ["Entry-Level React Developer", "Junior Web Developer", "Frontend Intern", "UI Developer Trainee", "Junior Software Engineer"]

        Resume text:
        {resume_text}
        """
        
        response = model.generate_content(prompt)
        print("🚦 3. AI finished generating!")
        
        # Clean the response and parse it into an actual Python list
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        suggested_roles = json.loads(cleaned_response)
        
        print("🚦 4. Ready to send back to frontend!")
        return {
            "raw_text": resume_text,
            "suggested_roles": suggested_roles
        }
        
    except Exception as e:
        print(f"❌ Error during resume processing / AI generation: {e}")
        return {"error": str(e)}

# --- NODE 1 (THE SCOUT) ---
async def fetch_jobs(search_query: str, is_remote: bool):
    params = {
        "engine": "google_jobs",
        "q": search_query,
        "hl": "en",
        "api_key": os.getenv("SERPAPI_KEY"),
    }
    
    # NATIVE REMOTE FILTER: Taps into Google's specific "Work from home" database
    if is_remote:
        params["ltype"] = "1"
        
    async with httpx.AsyncClient() as client:
        response = await client.get("https://serpapi.com/search", params=params)
        return response.json()

@app.get("/search-jobs")
async def search_jobs(role: str, location: str):
    # 1. Split out multiple roles
    target_roles = role.split(" OR ")
    
    # 2. Split out multiple locations
    if " in " in location:
        work_model, loc_str = location.split(" in ", 1)
        target_locations = loc_str.split(" OR ")
    else:
        work_model = location
        target_locations = [""]

    tasks = []
    is_remote = (work_model == "Remote")
    
    # 3. Loop through every combination of Role + Location concurrently
    for single_role in target_roles:
        for single_loc in target_locations:
            
            query = single_role
            
            # ANTI-SENIORITY FILTER: Force Google to drop senior roles if searching for junior
            if "junior" in single_role.lower() or "entry" in single_role.lower() or "intern" in single_role.lower() or "trainee" in single_role.lower() or "associate" in single_role.lower():
                query += " -senior -lead -principal -manager -director"
            
            # Only append location string if it is NOT remote
            if not is_remote and single_loc:
                query += f" in {single_loc}"
                
            tasks.append(fetch_jobs(query, is_remote))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_jobs = []
    seen_jobs = set() # Stops duplicate job listings
    
    for data in results:
        if isinstance(data, dict) and "jobs_results" in data:
            # We slice to 10 since our queries are much more accurate with the new filters
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
    """Replaces multiple endpoints to save 66% of API quota."""
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
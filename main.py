from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
import json
import PyPDF2
import io
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows any frontend to connect (good for local testing)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correct model name: gemini-1.5-flash
model = genai.GenerativeModel('gemini-3.5-flash')

class JobData(BaseModel):
    description: str

class AlignmentData(BaseModel):
    resume_text: str
    target_skills: str

class EmailData(BaseModel):
    company_name: str
    role_title: str
    resume_points: str

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
        
        resume_text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                resume_text += extracted

        print("🚦 2. PDF read successfully! Sending to AI...")
        
        # 2. Ask Gemini to analyze the resume and suggest 5 roles
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
@app.get("/search-jobs")
async def search_jobs(role: str, location: str):
    # 1. Split out multiple roles
    target_roles = role.split(" OR ")
    
    # 2. Split out multiple locations (e.g. "Remote in Austin OR Dallas")
    if " in " in location:
        work_model, loc_str = location.split(" in ", 1)
        target_locations = loc_str.split(" OR ")
    else:
        work_model = location
        target_locations = [""]

    all_jobs = []
    seen_jobs = set() # Stops duplicate job listings
    
    # 3. Loop through every combination of Role + Location
    for single_role in target_roles:
        for single_loc in target_locations:
            
            # Build a clean, direct query for Google
            search_query = f"{single_role} {work_model}"
            if single_loc:
                search_query += f" in {single_loc}"
                
            params = {
                "engine": "google_jobs",
                "q": search_query,
                "hl": "en",
                "api_key": os.getenv("SERPAPI_KEY"),
            }
            
            try:
                response = requests.get("https://serpapi.com/search", params=params)
                data = response.json()
                
                if "jobs_results" in data:
                    for job in data["jobs_results"][:5]: 
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
            except Exception as e:
                print(f"API Error for {search_query}: {e}")
                
    return {"jobs_found": all_jobs}

# --- NODE 2 (THE PARSER) ---
@app.post("/extract-keywords")
def extract_keywords(job: JobData):
    prompt = f"""
    You are an expert Technical Recruiter. Read the following job description and extract 
    the top 5 most critical technical skills required for the role. 
    Return ONLY a comma-separated list of the skills, nothing else.
    
    Job Description:
    {job.description}
    """
    response = model.generate_content(prompt)
    return {"extracted_skills": response.text.strip()}

# --- NODE 3 (THE ALIGNER) ---
@app.post("/align-resume")
def align_resume(data: AlignmentData):
    prompt = f"""
    You are an elite Resume Writer. Take the user's raw resume text and optimize it 
    specifically to highlight these target skills: {data.target_skills}.
    Rewrite up to 3 project or work bullet points to match these keywords naturally without lying.
    
    Raw Resume Text:
    {data.resume_text}
    """
    response = model.generate_content(prompt)
    return {"aligned_resume": response.text.strip()}

# --- NODE 4 (THE DRAFTER) ---
@app.post("/draft-email")
def draft_email(data: EmailData):
    prompt = f"""
    You are an expert career coach. Write a short, highly professional cold outreach email
    to a recruiter at {data.company_name} for the {data.role_title} role.
    
    Use the following optimized resume points to prove the candidate's value:
    {data.resume_points}
    
    Keep the email under 150 words. Be confident but polite. 
    Only use a placeholder for the user's signature at the very bottom.
    """
    
    response = model.generate_content(prompt)
    return {"cold_email": response.text.strip()}
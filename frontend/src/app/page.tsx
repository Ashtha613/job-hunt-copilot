"use client";
import { useState } from "react";

const API_BASE_URL = "https://job-hunt-copilot-egwq.onrender.com";

export default function Home() {
  // --- STATE MANAGEMENT ---
  const [warning, setWarning] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [suggestedRoles, setSuggestedRoles] = useState<string[]>([]);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  
  const [workModel, setWorkModel] = useState("On-site");
  const [loc1, setLoc1] = useState("");
  const [loc2, setLoc2] = useState("");
  const [loc3, setLoc3] = useState("");

  const [jobs, setJobs] = useState<any[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isScouting, setIsScouting] = useState(false);
  
  const [generatingIndex, setGeneratingIndex] = useState<number | null>(null);
  const [generatedEmail, setGeneratedEmail] = useState("");

  // --- LOGIC ---
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsAnalyzing(true);
    setWarning("");
    setSuggestedRoles([]);
    setSelectedRoles([]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/upload-resume`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      
      if (data.error) {
        const errorString = data.error.toLowerCase();
        if (errorString.includes("429") || errorString.includes("quota") || errorString.includes("limit")) {
          setWarning("You've hit your daily AI limit! The free tier clocked out 😭 See you tomorrow.");
        } else if (errorString.includes("timeout")) {
          setWarning("The server is taking too long to respond. Give it a few seconds and try again.");
        } else {
          setWarning("Oops! Something went wrong behind the scenes while reading your resume. Please try again.");
        }
        setSuggestedRoles([]);
        setResumeText("");
      } else {
        setResumeText(data.raw_text || "");
        setSuggestedRoles(data.suggested_roles || []); 
      }
    } catch (error) {
      console.error(error);
      setWarning("We couldn't connect to the server to analyze your resume. Please check your connection.");
    }
    setIsAnalyzing(false);
  };

  const toggleRole = (role: string) => {
    setSelectedRoles(prev => 
      prev.includes(role) ? prev.filter(r => r !== role) : [...prev, role]
    );
  };

  const searchForJobs = async () => {
    setWarning(""); 
    setJobs([]);
    
    if (selectedRoles.length === 0) {
      setWarning("Please select at least one target role before searching!");
      return;
    }
    
    const activeLocations = [loc1, loc2, loc3].filter(l => l.trim() !== "");
    if (workModel !== "Remote" && !loc1.trim()) {
      setWarning(`Please enter at least one primary city for your ${workModel} job search!`);
      return;
    }
    
    setIsScouting(true);
    try {
      const combinedRoles = selectedRoles.join(" OR ");
      let locationQuery = workModel;
      if (activeLocations.length > 0) {
         locationQuery += " in " + activeLocations.join(" OR ");
      }
      
      const response = await fetch(`${API_BASE_URL}/search-jobs?role=${combinedRoles}&location=${locationQuery}`);
      const data = await response.json();
      
      if (!data.jobs_found || data.jobs_found.length === 0) {
        setWarning("We couldn't find any jobs matching those exact criteria right now. Try adjusting your roles or locations!");
      } else {
        setJobs(data.jobs_found);
      }
    } catch (error) {
      console.error(error);
      setWarning("We couldn't reach the job database right now. Please wait a moment and try again.");
    }
    setIsScouting(false);
  };

  const generateColdEmail = async (job: any, index: number) => {
    if (!resumeText) {
      setWarning("Please upload your resume in Step 1 first so we have context to write the email!");
      return;
    }
    setGeneratingIndex(index);
    setGeneratedEmail("");
    setWarning("");

    try {
      const response = await fetch(`${API_BASE_URL}/generate-outreach`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
            job_description: job.description,
            resume_text: resumeText,
            company_name: job.company, 
            role_title: job.title 
        })
      });
      
      const data = await response.json();
      
      if (data.error) {
        const errorString = data.error.toLowerCase();
        if (errorString.includes("429") || errorString.includes("quota")) {
          setWarning("You've hit your daily AI limit! The free tier clocked out 😭 See you tomorrow.");
        } else {
          setWarning("Our AI writer ran into a snag. Please try drafting the email again.");
        }
      } else {
          setGeneratedEmail(data.cold_email);
      }
      
    } catch (error) {
      console.error(error);
      setWarning("The AI writer lost its train of thought. Please check your connection and try again.");
    }
    setGeneratingIndex(null);
  };

  // --- RENDER ---
  return (
    <main className="min-h-screen bg-[#f0f6f7] text-[#185e77] p-6 sm:p-10 font-sans pb-32">
      <div className="max-w-4xl mx-auto space-y-8">
        
        {/* HEADER */}
        <div className="text-center space-y-3 mb-12 pt-8">
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-[#185e77]">Job Hunt Copilot</h1>
          <p className="text-[#10899e] text-lg max-w-2xl mx-auto font-medium">Upload your resume, target your market, and draft personalized outreach.</p>
        </div>

        {/* STEP 1: RESUME UPLOAD */}
        <div className="bg-white border border-[#82b8b9]/30 shadow-sm p-8 rounded-2xl space-y-6">
           <div className="flex items-center space-x-3">
             <div className="h-8 w-8 rounded-full bg-[#185e77] flex items-center justify-center text-white font-bold text-sm">1</div>
             <h2 className="text-xl font-bold text-[#185e77] tracking-tight">AI Resume Profiler <span className="text-red-500">*</span></h2>
           </div>
           
           <div className="border-2 border-dashed border-[#82b8b9] bg-[#f0f6f7]/50 hover:bg-[#f0f6f7] transition-colors duration-200 rounded-xl p-8 text-center relative">
             <input type="file" accept=".pdf" onChange={handleFileUpload} className="block w-full text-sm text-[#185e77] file:mr-4 file:py-2.5 file:px-5 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-[#10899e] file:text-white hover:file:bg-[#185e77] cursor-pointer mx-auto transition-all" />
             {isAnalyzing && (
               <div className="absolute inset-0 bg-white/90 backdrop-blur-sm rounded-xl flex items-center justify-center">
                 <p className="text-[#10899e] font-medium flex items-center gap-2">Extracting optimal roles...</p>
               </div>
             )}
           </div>

           {suggestedRoles?.length > 0 && (
             <div className="bg-[#f0f6f7] p-5 rounded-xl border border-[#82b8b9]/40 mt-6">
               {/* Moved * next to the label */}
               <label className="block text-sm font-semibold text-[#185e77] uppercase tracking-wider">
                 Select Target Roles <span className="text-red-500">*</span>
               </label>
               <p className="text-sm text-[#10899e] mb-4 mt-1 font-medium">Please select at least one role below</p>
               <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                 {suggestedRoles.map((role) => (
                   <label key={role} className="flex items-center space-x-3 bg-white p-3.5 rounded-lg cursor-pointer hover:border-[#10899e] border border-[#82b8b9]/50 transition-all shadow-sm">
                     <input type="checkbox" checked={selectedRoles.includes(role)} onChange={() => toggleRole(role)} className="form-checkbox h-5 w-5 text-[#10899e] rounded border-[#82b8b9] focus:ring-[#10899e]" />
                     <span className="text-[#185e77] font-medium">{role}</span>
                   </label>
                 ))}
               </div>
             </div>
           )}
        </div>

        {/* STEP 2: LOCATION */}
        <div className="bg-white border border-[#82b8b9]/30 shadow-sm p-8 rounded-2xl space-y-6">
           <div className="flex items-center space-x-3">
             <div className="h-8 w-8 rounded-full bg-[#185e77] flex items-center justify-center text-white font-bold text-sm">2</div>
             <h2 className="text-xl font-bold text-[#185e77] tracking-tight">Target Location</h2>
           </div>
           
           <div>
             <label className="block text-sm font-semibold mb-3 text-[#185e77] uppercase tracking-wider">Work Model</label>
             <div className="flex p-1 bg-[#f0f6f7] rounded-xl border border-[#82b8b9]/40">
               {["On-site", "Hybrid", "Remote"].map(model => (
                 <button key={model} onClick={() => setWorkModel(model)} className={`flex-1 py-2.5 rounded-lg font-semibold text-sm transition-all duration-200 ${workModel === model ? "bg-white text-[#10899e] shadow-sm border border-[#82b8b9]/60" : "text-[#82b8b9] hover:text-[#185e77] hover:bg-white/50"}`}>
                   {model}
                 </button>
               ))}
             </div>
           </div>

           <div className="space-y-3">
             <label className="block text-sm font-semibold mb-1 text-[#185e77] uppercase tracking-wider mt-4">
               {workModel === "Remote" ? "Target Timezone / Region" : (
                 <>Target Cities <span className="text-red-500">*</span></>
               )}
             </label>

             {workModel === "Remote" ? (
               <input className="w-full p-3.5 bg-white rounded-lg border border-[#82b8b9] focus:border-[#10899e] focus:ring-1 focus:ring-[#10899e] focus:outline-none transition-all placeholder-[#82b8b9] text-[#185e77] shadow-sm" placeholder="e.g. US Only, EST Timezone (Optional)" value={loc1} onChange={(e) => setLoc1(e.target.value)} />
             ) : (
               <>
                 <input className="w-full p-3.5 bg-white rounded-lg border border-[#82b8b9] focus:border-[#10899e] focus:ring-1 focus:ring-[#10899e] focus:outline-none transition-all placeholder-[#82b8b9] text-[#185e77] shadow-sm" placeholder="Location 1 (Required, e.g. Austin, TX)" value={loc1} onChange={(e) => setLoc1(e.target.value)} />
                 <input className="w-full p-3.5 bg-white rounded-lg border border-[#82b8b9] focus:border-[#10899e] focus:ring-1 focus:ring-[#10899e] focus:outline-none transition-all placeholder-[#82b8b9] text-[#185e77] shadow-sm" placeholder="Location 2 (Optional)" value={loc2} onChange={(e) => setLoc2(e.target.value)} />
                 <input className="w-full p-3.5 bg-white rounded-lg border border-[#82b8b9] focus:border-[#10899e] focus:ring-1 focus:ring-[#10899e] focus:outline-none transition-all placeholder-[#82b8b9] text-[#185e77] shadow-sm" placeholder="Location 3 (Optional)" value={loc3} onChange={(e) => setLoc3(e.target.value)} />
               </>
             )}
           </div>

           <button onClick={searchForJobs} disabled={isScouting} className="w-full bg-[#10899e] text-white hover:bg-[#185e77] disabled:bg-[#82b8b9]/40 disabled:text-white disabled:cursor-not-allowed font-bold py-4 px-4 rounded-xl transition-all mt-4 text-base tracking-wide shadow-sm">
             {isScouting ? "Searching databases..." : "Run Job Search"}
           </button>
        </div>

        {/* WARNING BANNER */}
        {warning && (
          <div className="bg-red-50 border border-red-400 p-4 rounded-xl text-red-700 font-semibold flex items-center shadow-sm">
            <span className="mr-2 text-xl">⚠️</span> {warning}
          </div>
        )}

        {/* STEP 3: LIVE JOB MATCHES */}
        {jobs.length > 0 && (
          <div className="bg-white border border-[#82b8b9]/30 shadow-sm p-8 rounded-2xl space-y-6">
            <div className="flex items-center space-x-3 mb-2">
               <div className="h-8 w-8 rounded-full bg-[#185e77] flex items-center justify-center text-white font-bold text-sm">3</div>
               <h2 className="text-xl font-bold text-[#185e77] tracking-tight">Select a Target</h2>
            </div>
            
            <div className="space-y-4">
              {jobs.map((job, index) => (
                <div key={index} className="bg-white p-5 rounded-xl border border-[#82b8b9]/50 hover:border-[#10899e] hover:shadow-md transition-all flex flex-col space-y-4">
                  <div>
                    <h3 className="text-lg font-bold text-[#185e77]">{job.title}</h3>
                    <p className="text-[#10899e] font-medium text-sm mt-1">{job.company}</p>
                    <p className="text-[#185e77]/70 text-sm mt-3 leading-relaxed line-clamp-2">{job.description}</p>
                  </div>
                  
                  <div className="flex flex-col sm:flex-row gap-3 pt-2">
                    <button onClick={() => generateColdEmail(job, index)} disabled={generatingIndex !== null} className="flex-1 bg-[#f0f6f7] text-[#185e77] hover:bg-[#82b8b9]/20 border border-[#82b8b9] disabled:opacity-50 font-semibold py-2.5 px-4 rounded-lg transition-all text-sm">
                      {generatingIndex === index ? "Drafting..." : "Draft Outreach Email"}
                    </button>
                    
                    <a href={job.apply_link || "#"} target="_blank" rel="noopener noreferrer" className="flex-1 bg-[#10899e] hover:bg-[#185e77] text-white font-semibold py-2.5 px-4 rounded-lg transition-all text-sm text-center flex items-center justify-center">
                      Apply Now <span className="ml-2 opacity-70">↗</span>
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STEP 4: EMAIL OUTPUT */}
        {generatedEmail && (
          <div className="bg-[#185e77] p-8 rounded-2xl shadow-xl border border-[#10899e] space-y-5">
            <div className="flex items-center space-x-3">
               <div className="h-8 w-8 rounded-full bg-[#f0f6f7] flex items-center justify-center text-[#185e77] font-bold text-sm">4</div>
               <h2 className="text-xl font-bold text-white tracking-tight">Final Output</h2>
            </div>
            <div className="bg-white/10 p-5 rounded-xl border border-[#82b8b9]/30 whitespace-pre-wrap text-[#f0f6f7] font-mono text-sm leading-relaxed">
              {generatedEmail}
            </div>
          </div>
        )}

      </div>
    </main>
  );
}
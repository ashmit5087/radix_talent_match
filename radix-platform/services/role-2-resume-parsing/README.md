# Resume Parsing (Role 2) — RADIX Talent Match

Resume (PDF/DOCX) in  ->  JSON skill list (shared ResumeExtract format) out.
Output goes to `output/<name>_pdf.json` / `output/<name>_docx.json` for Profile Builder.

## Setup (once)
    python -m venv venv
    source venv/bin/activate         # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env             # Windows: copy .env.example .env

Then fill in `.env` (keys from https://console.groq.com/keys):

    GROQ_API_KEY=your_key_here
    GROQ_API_KEY_2=second_key        # optional, used when the first is rate-limited
    GROQ_API_KEY_3=third_key         # optional
    GROQ_MODEL=openai/gpt-oss-120b

Put the sample resumes (PDF + DOCX) in `samples/`.

## Steps

### Step 1 — Shared format (`schema.py`)
The data structure shared by JD Analytics (Role 1) and Resume Parsing (Role 2).
Both roles import from this one file so the output always matches.
Same copy as JD Analytics; change only together.

### Step 2 — Read the resume (`read_file.py`)
Pulls plain text out of a resume (PDF or DOCX). Test it on its own (milestone 7):

    python read_file.py "samples/Ananya Rao.pdf"

### Step 3 — Extract skills (`extract.py`)
Sends the resume text to Groq (via LangChain) and gets skills, education, projects,
experience and certifications back in the shared ResumeExtract format.
Removes duplicate skills, retries on bad output, and switches to the next API key
when one is rate-limited (it only waits when all keys are). Test one resume:

    python extract.py "samples/Ananya Rao.pdf"

### Step 4 — Run on resumes (`parse_resume.py`)
Main runner. Parses one resume or a whole folder and saves two JSON files per resume:
- `output/<name>.json` — full ResumeExtract format (category code, evidence, confidence)
- `output/simple/<name>.json` — same details, but skills as plain names only

One file:

    python parse_resume.py "samples/Ananya Rao.pdf"

Whole folder (milestone 8):

    python parse_resume.py samples

### Step 5 — Check the output (`check_output.py`)
Checks the JSON files in `output/` before handing them to Profile Builder.
No API key needed.
- Confirms every file matches the shared ResumeExtract format
- Prints a skill count per category for each candidate, so you can see
  whether different candidates come out visibly different

      python check_output.py

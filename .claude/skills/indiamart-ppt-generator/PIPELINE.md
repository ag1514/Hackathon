# Pipeline - Runnable Code Reference

All blocks run from the project root.
Replace {leader} with profile stem: ceo, cto, vp_sales, vp_product.
Replace {user_instructions} with context the user provided (empty string if none).

---

## Phase 0-G - Gmail Authentication & Search

### Step 1: Authenticate

```python
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
creds  = None
if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow  = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
    with open("token.json", "w") as f:
        f.write(creds.to_json())
from googleapiclient.discovery import build
service = build("gmail", "v1", credentials=creds)
profile = service.users().getProfile(userId="me").execute()
print(f"Connected as: {profile.get('emailAddress', 'unknown')}")
```

First-time auth opens a browser for OAuth consent. After approval, `token.json` is saved and reused on future runs.
If the browser does not open automatically, copy the URL printed in the terminal and paste it manually.

---

### Step 2: Search emails

```python
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from core.gmail_client import build_query, list_emails

SCOPES  = ["https://www.googleapis.com/auth/gmail.readonly"]
creds   = Credentials.from_authorized_user_file("token.json", SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
service = build("gmail", "v1", credentials=creds)

query = build_query(
    keyword     = "{search_keyword}",
    from_email  = "",          # e.g. "manager@indiamart.com" or empty
    after_date  = None,        # e.g. "2026-04-01"
    before_date = None,        # e.g. "2026-05-01"
    label       = "All",       # "Inbox", "Sent", "Starred", "Important", "All"
)
emails = list_emails(service, query, max_results=25)

for i, em in enumerate(emails, 1):
    print(f"{i:2}. [{em['date'][:10]}] {em['from'][:30]:30} | {em['subject'][:50]}")

import os; os.makedirs("temp", exist_ok=True)
with open("temp/gmail_search.json", "w", encoding="utf-8") as f:
    json.dump(emails, f, indent=2, ensure_ascii=False)
print(f"\n{len(emails)} threads found.")
```

Present the numbered list. Ask: "Which threads? (e.g. '1,3,5' or 'all')"

---

### Step 3: Fetch selected threads

```python
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from core.gmail_client import get_thread_messages

SCOPES  = ["https://www.googleapis.com/auth/gmail.readonly"]
creds   = Credentials.from_authorized_user_file("token.json", SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
service = build("gmail", "v1", credentials=creds)

with open("temp/gmail_search.json", encoding="utf-8") as f:
    all_threads = json.load(f)

selected_indices = [0, 2, 4]   # 0-based; user said "1,3,5" -> use [0,2,4]
selected = [all_threads[i] for i in selected_indices if i < len(all_threads)]

thread_data = {}
for t in selected:
    msgs = get_thread_messages(service, t["threadId"])
    thread_data[t["threadId"]] = {"meta": t, "messages": msgs}

with open("temp/gmail_threads.json", "w", encoding="utf-8") as f:
    json.dump(thread_data, f, indent=2, ensure_ascii=False)
print(f"Fetched {len(thread_data)} threads.")
```

---

### Step 4: Download email attachments

```python
import json, os, re
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from core.gmail_client import download_attachment

SCOPES  = ["https://www.googleapis.com/auth/gmail.readonly"]
creds   = Credentials.from_authorized_user_file("token.json", SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
service = build("gmail", "v1", credentials=creds)

with open("temp/gmail_threads.json", encoding="utf-8") as f:
    thread_data = json.load(f)

os.makedirs("temp", exist_ok=True)
att_paths = []
for tid, tinfo in thread_data.items():
    for msg in tinfo.get("messages", []):
        for att in msg.get("attachments", []):
            try:
                data = download_attachment(service, att)
                safe = re.sub(r"[^A-Za-z0-9._-]", "_", att["filename"])
                path = f"temp/gmail_att_{safe}"
                with open(path, "wb") as f:
                    f.write(data)
                att_paths.append(path)
            except Exception as e:
                print(f"  Skipped {att.get('filename','?')}: {e}")

with open("temp/gmail_att_paths.json", "w") as f:
    json.dump(att_paths, f)
print(f"Downloaded {len(att_paths)} attachment(s).")
```

---

### Step 5: Extract from emails and attachments (replaces Phase 1 for gmail source)

```python
import json, os
from utils.claude_client import ClaudeClient
from core.content_extractor import ContentExtractor
from core.gmail_client import format_emails_for_extraction

with open("gateway_config.json") as f:
    cfg = json.load(f)
with open("temp/gmail_threads.json", encoding="utf-8") as f:
    thread_data = json.load(f)

claude = ClaudeClient(cfg["api_key"], cfg["gateway_url"], cfg["model_name"])
ext    = ContentExtractor(claude)

email_data_list = []
for tid, tinfo in thread_data.items():
    meta = tinfo["meta"]
    msgs = tinfo.get("messages", [])
    if msgs:
        email_data_list.append({
            "from":    msgs[0].get("from", meta.get("from", "")),
            "subject": meta.get("subject", "(no subject)"),
            "date":    msgs[0].get("date", meta.get("date", "")),
            "body":    msgs[0].get("body", ""),
            "replies": msgs[1:],
        })

formatted_text = format_emails_for_extraction(email_data_list)
content = ext.extract_from_emails(formatted_text, "{user_instructions}")

# Also extract from any downloaded attachments
if os.path.exists("temp/gmail_att_paths.json"):
    with open("temp/gmail_att_paths.json") as f:
        att_paths = json.load(f)
    if att_paths:
        att_content = ext.extract_from_files(att_paths, "{user_instructions}")
        for k in ["key_metrics","findings","achievements","challenges",
                  "recommendations","decisions_needed","chart_data","diagram_suggestions"]:
            if att_content.get(k):
                content[k] = content.get(k, []) + att_content[k]

os.makedirs("temp", exist_ok=True)
with open("temp/content.json", "w", encoding="utf-8") as f:
    json.dump(content, f, indent=2, ensure_ascii=False)
print(f"GMAIL EXTRACTION DONE - {len(content.get('key_metrics',[]))} metrics")
```

After Step 5, continue with Merging (if extra sources were provided) then Phase 2.

---

## Phase 1 - Primary Content Extraction

### Mode A: Text

```python
import json, os
os.makedirs("temp", exist_ok=True)
from utils.claude_client import ClaudeClient
from core.content_extractor import ContentExtractor

with open("gateway_config.json") as f:
    cfg = json.load(f)
claude = ClaudeClient(cfg["api_key"], cfg["gateway_url"], cfg["model_name"])
ext    = ContentExtractor(claude)

user_text = "PASTE_USER_CONTENT_HERE"
content   = ext.extract_from_text(user_text, "{user_instructions}")

with open("temp/content.json", "w", encoding="utf-8") as f:
    json.dump(content, f, indent=2, ensure_ascii=False)
print(f"EXTRACTION DONE - {len(content.get('key_metrics',[]))} metrics")
```

### Mode B: Files (PDF, Excel, CSV, DOCX, TXT, PPTX)

```python
import json, os
os.makedirs("temp", exist_ok=True)
from utils.claude_client import ClaudeClient
from core.content_extractor import ContentExtractor

with open("gateway_config.json") as f:
    cfg = json.load(f)
claude = ClaudeClient(cfg["api_key"], cfg["gateway_url"], cfg["model_name"])
ext    = ContentExtractor(claude)

file_paths = [
    r"C:\path\to\file1.xlsx",
    # add more paths as needed
]
content = ext.extract_from_files(file_paths, "{user_instructions}")

with open("temp/content.json", "w", encoding="utf-8") as f:
    json.dump(content, f, indent=2, ensure_ascii=False)
print(f"EXTRACTION DONE - {len(content.get('key_metrics',[]))} metrics")
```

### Mode C: URL

```python
import json, os
os.makedirs("temp", exist_ok=True)
from utils.claude_client import ClaudeClient
from core.content_extractor import ContentExtractor

with open("gateway_config.json") as f:
    cfg = json.load(f)
claude = ClaudeClient(cfg["api_key"], cfg["gateway_url"], cfg["model_name"])
ext    = ContentExtractor(claude)

content = ext.extract_from_url("{the_url}", "{user_instructions}")

with open("temp/content.json", "w", encoding="utf-8") as f:
    json.dump(content, f, indent=2, ensure_ascii=False)
print(f"EXTRACTION DONE - {len(content.get('key_metrics',[]))} metrics")
```

### Mode D: Topic keyword

```python
import json, os
os.makedirs("temp", exist_ok=True)
from utils.claude_client import ClaudeClient
from core.content_extractor import ContentExtractor

with open("gateway_config.json") as f:
    cfg = json.load(f)
claude = ClaudeClient(cfg["api_key"], cfg["gateway_url"], cfg["model_name"])
ext    = ContentExtractor(claude)

content = ext.extract_from_topic("{topic_keyword}", "{user_instructions}")

with open("temp/content.json", "w", encoding="utf-8") as f:
    json.dump(content, f, indent=2, ensure_ascii=False)
print("EXTRACTION DONE")
```

### Mode E: Update existing PPT

```python
import json, os
os.makedirs("temp", exist_ok=True)
from utils.claude_client import ClaudeClient
from core.content_extractor import ContentExtractor

with open("gateway_config.json") as f:
    cfg = json.load(f)
claude = ClaudeClient(cfg["api_key"], cfg["gateway_url"], cfg["model_name"])
ext    = ContentExtractor(claude)

old_ppt_path   = r"C:\path\to\existing.pptx"
new_data_paths = [r"C:\path\to\new_data.xlsx"]  # or []
new_text       = ""   # any new text context, or empty string
context        = "{user_instructions}"

content = ext.extract_from_previous_ppt(old_ppt_path, new_data_paths, new_text, context)

with open("temp/content.json", "w", encoding="utf-8") as f:
    json.dump(content, f, indent=2, ensure_ascii=False)
print(f"EXTRACTION DONE - {len(content.get('key_metrics',[]))} metrics")
```

---

## Merging - Additional Sources

Run any applicable block AFTER primary extraction. Each reads temp/content.json, merges, and writes back.

```python
import json, os
from utils.claude_client import ClaudeClient
from core.content_extractor import ContentExtractor

with open("gateway_config.json") as f:
    cfg = json.load(f)
with open("temp/content.json", encoding="utf-8") as f:
    content = json.load(f)

claude = ClaudeClient(cfg["api_key"], cfg["gateway_url"], cfg["model_name"])
ext    = ContentExtractor(claude)
ctx    = "{user_instructions}"
LIST_KEYS = ["key_metrics","findings","achievements","challenges",
             "recommendations","decisions_needed","chart_data","diagram_suggestions"]

def merge(base, addition):
    for k in LIST_KEYS:
        if addition.get(k):
            base[k] = base.get(k, []) + addition[k]
    if not base.get("title_suggestion") and addition.get("title_suggestion"):
        base["title_suggestion"] = addition["title_suggestion"]
    if addition.get("_uploaded_images"):
        base.setdefault("_uploaded_images", []).extend(addition["_uploaded_images"])
    return base

# Uncomment whichever apply:

# Extra URL:
# c = ext.extract_from_url("{extra_url}", ctx); content = merge(content, c)

# Extra documents or data files:
# c = ext.extract_from_files([r"C:\path\to\doc.pdf"], ctx); content = merge(content, c)

# Extra images / screenshots (stored as proof-of-work slides):
# image_paths = [r"C:\path\to\screenshot.png"]
# content.setdefault("_uploaded_images", []).extend(image_paths)
# if "{extra_image_context}":
#     c = ext.extract_from_text(f"Screenshots uploaded: {image_paths}. Context: {extra_image_context}",
#                               "Incorporate these images into relevant slides as proof of work.")
#     content = merge(content, c)

# GitHub repo:
# c = ext.extract_from_github("{github_url}", ctx); content = merge(content, c)

# OpenProject tickets:
# c = ext.extract_from_openproject("{openproject_url}", "{api_key}", "{project_name_or_None}", ctx)
# content = merge(content, c)

# Google Sheets (must be publicly shared):
# c = ext.extract_from_google_sheet("{sheets_url}", ctx); content = merge(content, c)

with open("temp/content.json", "w", encoding="utf-8") as f:
    json.dump(content, f, indent=2, ensure_ascii=False)
print("Merge complete.")
```

---

## Phase 2 - Slide Planning

Reads: temp/content.json
Writes: temp/plan.json

```python
import json, yaml
from utils.claude_client import ClaudeClient
from core.ppt_agent import PPTAgent

with open("gateway_config.json") as f:
    cfg = json.load(f)
with open("temp/content.json", encoding="utf-8") as f:
    content = json.load(f)
with open("profiles/{leader}.yml", encoding="utf-8") as f:
    profile = yaml.safe_load(f)

claude = ClaudeClient(cfg["api_key"], cfg["gateway_url"], cfg["model_name"])
agent  = PPTAgent(claude)
result = agent.plan(content, profile, user_instructions="{user_instructions}")

with open("temp/plan.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

slide_plan = result.get("slide_plan", result) if isinstance(result, dict) else result
print(f"PLANNING DONE - {len(slide_plan)} slides")
```

---

## Phase 3 - Plan Editing (interactive)

See SKILL.md Phase 3 for the conversational flow.

Edit helper - run when user requests changes:

```python
import json
with open("temp/plan.json", encoding="utf-8") as f:
    plan_result = json.load(f)
slide_plan = plan_result.get("slide_plan", plan_result) if isinstance(plan_result, dict) else plan_result

# Remove slide at index 2 (0-based):
del slide_plan[2]

# Move slide from index 4 to position 1:
slide = slide_plan.pop(4)
slide_plan.insert(1, slide)

# Renumber after ANY change:
for i, s in enumerate(slide_plan):
    s["slide_number"] = i + 1

if isinstance(plan_result, dict):
    plan_result["slide_plan"] = slide_plan
else:
    plan_result = slide_plan

with open("temp/plan.json", "w", encoding="utf-8") as f:
    json.dump(plan_result, f, indent=2, ensure_ascii=False)
print("Plan updated.")
```

---

## Phase 4 - Slide Generation

Reads: temp/plan.json, temp/content.json
Writes: temp/slide_contents.json

```python
import json, yaml
from utils.claude_client import ClaudeClient
from core.ppt_agent import PPTAgent

with open("gateway_config.json") as f:
    cfg = json.load(f)
with open("temp/plan.json", encoding="utf-8") as f:
    plan_result = json.load(f)
with open("temp/content.json", encoding="utf-8") as f:
    content = json.load(f)
with open("profiles/{leader}.yml", encoding="utf-8") as f:
    profile = yaml.safe_load(f)

claude     = ClaudeClient(cfg["api_key"], cfg["gateway_url"], cfg["model_name"])
agent      = PPTAgent(claude)
slide_plan = plan_result.get("slide_plan", plan_result) if isinstance(plan_result, dict) else plan_result

slide_contents = agent.generate_all(slide_plan, content, profile)

# Pad if LLM truncated response
while len(slide_contents) < len(slide_plan):
    i = len(slide_contents)
    p = slide_plan[i]
    slide_contents.append({
        "title":         p.get("title", f"Slide {i+1}"),
        "subtitle":      "",
        "bullets":       ["Content unavailable - edit in PowerPoint."],
        "key_callout":   "",
        "speaker_notes": "",
        "slide_number":  p.get("slide_number", i+1),
        "slide_type":    p.get("slide_type", "content"),
        "layout":        p.get("layout", "bullets"),
    })

with open("temp/slide_contents.json", "w", encoding="utf-8") as f:
    json.dump(slide_contents, f, indent=2, ensure_ascii=False)
print(f"GENERATION DONE - {len(slide_contents)} slides written")
```

---

## Phase 5 - PPT Rendering

Reads: temp/plan.json, temp/slide_contents.json
Writes: output/presentation_{leader}_{timestamp}.pptx

```python
import json, yaml, os
from datetime import datetime
from utils.claude_client import ClaudeClient
from core.ppt_renderer import PPTRenderer
from core.chart_generator import ChartGenerator
from core.diagram_generator import DiagramGenerator

with open("gateway_config.json") as f:
    cfg = json.load(f)
with open("temp/plan.json", encoding="utf-8") as f:
    plan_result = json.load(f)
with open("temp/slide_contents.json", encoding="utf-8") as f:
    slide_contents = json.load(f)
with open("profiles/{leader}.yml", encoding="utf-8") as f:
    profile = yaml.safe_load(f)

os.makedirs("temp", exist_ok=True)
os.makedirs("output", exist_ok=True)

claude      = ClaudeClient(cfg["api_key"], cfg["gateway_url"], cfg["model_name"])
renderer    = PPTRenderer(profile)
chart_gen   = ChartGenerator()
diagram_gen = DiagramGenerator(claude)

slide_plan  = plan_result.get("slide_plan", plan_result) if isinstance(plan_result, dict) else plan_result
content_map = {s["slide_number"]: s for s in slide_contents}

for plan_slide in slide_plan:
    num = plan_slide["slide_number"]
    sc  = content_map.get(num, {})

    if plan_slide.get("slide_type") == "title":
        renderer.add_title_slide(
            title    = sc.get("title", plan_slide.get("title", "")),
            subtitle = sc.get("subtitle", ""),
            date     = datetime.now().strftime("%B %Y"),
        )
        continue

    chart_path = diagram_path = None
    if sc.get("chart_spec"):
        chart_path = f"temp/chart_{num}.png"
        try:
            chart_gen.generate(sc["chart_spec"], chart_path)
        except Exception as e:
            print(f"  Chart {num} failed: {e}"); chart_path = None
    if sc.get("diagram_spec"):
        diagram_path = f"temp/diagram_{num}.png"
        try:
            diagram_gen.generate_placeholder_image(sc["diagram_spec"], diagram_path)
        except Exception as e:
            print(f"  Diagram {num} failed: {e}"); diagram_path = None

    renderer.add_content_slide(sc, chart_path=chart_path, diagram_path=diagram_path)

# --- Proof-of-work screenshot slides ---
# Set proof_paths to a list of image file paths if the user provided screenshots.
# Leave as empty list [] if no proof screenshots.
proof_paths   = []   # e.g. [r"C:\path\to\screenshot1.png"]
proof_caption = ""   # e.g. "Live demo - Feature X in production"
for idx, img_path in enumerate(proof_paths, start=1):
    renderer.add_proof_slide(image_path=img_path, caption=proof_caption,
                             index=idx, total=len(proof_paths))

ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
leader = profile.get("name", "leader").lower().replace(" ", "_")
out    = f"output/presentation_{leader}_{ts}.pptx"
renderer.save(out)

from pptx import Presentation as _Prs
total_slides = len(_Prs(out).slides)
print(f"SAVED: {out}  ({total_slides} slides)")
```

### Proof slides note

`renderer.add_proof_slide(image_path, caption, index, total)` adds a dedicated slide with the
screenshot centred in the content area, aspect-ratio preserved, with an optional caption below.
Slide title is auto-generated: "Demo Screenshot N/Total" or "Demo / Proof of Work" for a single image.

---

## Output - Open file on Windows

After SAVED prints, open the file automatically in PowerPoint:

```python
import subprocess, os
out = "output/presentation_ceo_20260516_143022.pptx"   # replace with actual filename
subprocess.Popen(["start", "", os.path.abspath(out)], shell=True)
print("Opening in PowerPoint...")
```

---

## Preview Generation - Slide Images (optional, post-render)

Goal: Convert the saved .pptx to PNG images (one per slide) so you can inspect slides without opening PowerPoint.

Uses `utils/preview_generator.py` which tries two strategies in order:
1. **LibreOffice headless** (high fidelity, requires LibreOffice installed)
2. **Pillow fallback** (always works; reads shapes from python-pptx directly)

Output: 1280x720 PNG files, one per slide, in `temp/preview_{deck_name}/`.

```python
import os
from utils.preview_generator import generate_previews

# Replace with the actual output filename from Phase 5
pptx_path   = "output/presentation_ceo_20260516_143022.pptx"
preview_dir = "temp/preview_" + os.path.splitext(os.path.basename(pptx_path))[0]

png_paths = generate_previews(pptx_path, preview_dir)

print(f"Generated {len(png_paths)} preview images:")
for i, p in enumerate(png_paths, 1):
    print(f"  Slide {i}: {p}")
```

After running, the PNG files are in `temp/preview_presentation_ceo_.../`.
You can open any of them with the default image viewer on Windows:

```python
import subprocess, os
# Open slide 1 preview:
subprocess.Popen(["start", "", os.path.abspath(png_paths[0])], shell=True)

# Or open the whole preview folder in Explorer:
subprocess.Popen(["explorer", os.path.abspath(preview_dir)], shell=True)
```

### LibreOffice note

LibreOffice headless is checked automatically at common install paths
(`C:\Program Files\LibreOffice\program\soffice.exe`, etc.).
If it is not installed, the Pillow fallback runs automatically — no configuration needed.
To install LibreOffice for better preview fidelity: https://www.libreoffice.org/download/libreoffice/

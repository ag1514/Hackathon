---
name: indiamart-ppt-generator
description: Generate professional AI-powered PowerPoint presentations for Indiamart leadership. Use when the user asks to create a PPT, slides, or presentation for CEO, CTO, VP Sales, or VP Product. Supports text, file uploads, URLs, existing PPT updates, Gmail threads, GitHub repos, OpenProject tickets, and Google Sheets as input. Produces a branded .pptx via a 3-phase LLM pipeline (extract -> plan -> generate) using the Indiamart LLM gateway.
---

# Indiamart PPT Generator

A 5-phase pipeline that turns raw data into a branded, leader-tailored PowerPoint. The pipeline uses the **Indiamart LLM gateway** (configured in `gateway_config.json`) for all AI calls. Claude Code is the orchestrator; the gateway is the generator.

---

## Prerequisites

Verify these exist in the project root before starting:
- `gateway_config.json` - `{ "gateway_url": "...", "api_key": "...", "model_name": "..." }`
- `profiles/` - `ceo.yml`, `cto.yml`, `vp_sales.yml`, `vp_product.yml`
- `prompts.md` - all system prompts (auto-loaded by `utils/prompt_loader.py`)

If `gateway_config.json` is missing, ask user for credentials and write it.

---

## Phase 0 - Input Gathering (always start here)

### Required
1. **Leader** - CEO / CTO / VP Sales / VP Product
   - File map: CEO=ceo.yml, CTO=cto.yml, VP Sales=vp_sales.yml, VP Product=vp_product.yml
2. **Primary source** (pick one):
   - `text` - user pastes or describes content
   - `files` - local file paths (PDF, Excel, CSV, DOCX, TXT, PPTX)
   - `url` - a webpage URL
   - `topic` - keyword phrase; LLM generates representative content
   - `update_ppt` - update an existing .pptx with new data
   - `gmail` - pull content from Gmail threads (run Phase 0-G first)

### Optional additional sources (all combinable with primary)
- **Extra URL** - a second webpage merged into content
- **Extra documents** - additional PDF/DOCX/TXT/XLSX files
- **Extra data files** - CSV/Excel files
- **Extra images / screenshots** - embedded as proof-of-work slides
- **GitHub repo** - GitHub repository URL
- **OpenProject** - instance URL + API key + project name
- **Google Sheets** - publicly shared Sheets URL
- **Gmail threads** - can combine with any primary source

### Optional presentation settings
- **Context / instructions** - special focus, tone, talking points
- **Proof caption** - caption for proof-of-work screenshot slides

Do not proceed to Phase 1 without leader + at least one content source.

---

## Phase 0-G - Gmail Setup (only when gmail is a source)

1. Check `credentials.json` exists at project root (download from Google Cloud Console if missing)
2. Authenticate - run PIPELINE.md Phase 0-G Step 1 (reuses token.json; first-time opens browser)
3. Search - ask user for keyword, optional sender, optional date range; run Step 2
4. Select threads - show numbered list; ask which to include
5. Fetch thread bodies and replies - run Step 3
6. Download email attachments - run Step 4
7. Extract content - run Step 5 (extract_from_emails + extract_from_files for attachments)

Writes temp/content.json. Continue with extra sources (merging), then Phase 2.

---

## Phase 1 - Content Extraction

Goal: Convert primary source to structured content dict, write temp/content.json.

See PIPELINE.md Phase 1 for all runnable code blocks (one per primary mode).

**Multi-source merging** - run additional extractors for each extra source the user provided, then merge:
- Extra URL -> extract_from_url()
- Extra documents -> extract_from_files()
- Extra data files -> extract_from_files()
- Extra images -> store paths in content["_uploaded_images"]; extract context text if provided
- GitHub repo -> extract_from_github()
- OpenProject -> extract_from_openproject()
- Google Sheets -> extract_from_google_sheet()
- Gmail content -> already in temp/content.json from Phase 0-G; merge with merge_content()

See PIPELINE.md Merging section for the merge helper code.

After all sources merged, write final temp/content.json.

---

## Phase 2 - Slide Planning

See PIPELINE.md Phase 2. Writes temp/plan.json (slide_plan array + narrative strategy).

---

## Phase 3 - Interactive Plan Review

Read temp/plan.json, present the slide_plan as a numbered markdown list:

  Here is your {N}-slide plan for {Leader}:
  1. [title] - title
  2. [title] - executive_summary
  ...
  Say "looks good" or tell me what to change (add/remove/move/rename slides).

When user edits: apply to slide_plan list, renumber slide_number fields, write back to temp/plan.json, show revised list. Confirm before Phase 4.

---

## Phase 4 - Slide Generation

See PIPELINE.md Phase 4. May take 30-60 seconds. Writes temp/slide_contents.json.

---

## Phase 5 - PPT Rendering

See PIPELINE.md Phase 5. Assembles all slides, appends proof-of-work screenshot slides if provided, saves to output/.

---

## Output Delivery

1. Report the full output path to the user
2. On Windows, offer to open: run `start "" "output/presentation_....pptx"` via bash
3. Optionally generate slide previews (PNG per slide) - see PIPELINE.md Preview Generation section
4. Summarise: slide count, leader profile, content sources used

---

## Error Handling

| Error | Action |
|---|---|
| gateway_config.json not found | Ask user for credentials; write the file |
| KeyError in prompt_loader | prompts.md missing a section - check heading names |
| LLM returns empty/truncated JSON | Retry once; report raw response if still failing |
| File not found on extraction | Ask user to confirm exact absolute path |
| temp/content.json missing at Phase 2 | Re-run Phase 1 |
| Generation returns fewer slides than plan | Padding loop in Phase 4 fills gaps automatically |
| credentials.json missing for Gmail | Ask user to download from Google Cloud Console |
| Gmail OAuth browser does not open | Copy auth URL from terminal, paste into browser manually |
| Gmail token expired | Delete token.json, re-run Phase 0-G Step 1 |
| OpenProject key rejected | Verify API key has read access to the project |

"""
PPT Agent — the brain behind every presentation generated in this app.

Architecture:
  Call 1 (plan)         → STRATEGY: designs the narrative arc tailored to the leader
  Call 2 (generate_all) → GENERATION: writes ALL slides in one coherent pass

Everything the agent needs to know — Indiamart brand, leader psychology,
presentation thinking frameworks — lives in the SKILL constants below.
"""
import json
import os
from utils.claude_client import ClaudeClient
from utils.prompt_loader import get_prompt

_DEFAULT_TEMPLATE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "templates", "indiamart_default.pptx"
)

# ═══════════════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPTS — loaded from prompts.md at the project root
#  Edit prompts.md to tune LLM behaviour without touching this file.
# ═══════════════════════════════════════════════════════════════════════════════

def _build_system(intro_key: str) -> str:
    """Assemble a full system prompt from its intro section + the 3 shared skill blocks."""
    return "\n\n".join([
        get_prompt(intro_key),
        get_prompt("indiamart_brand_skill"),
        get_prompt("leader_profiles_skill"),
        get_prompt("thinking_framework_skill"),
    ])

STRATEGY_SYSTEM   = _build_system("strategy_system")
GENERATION_SYSTEM = _build_system("generation_system")

STRATEGY_PROMPT = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRATEGY REQUEST — Design the deck narrative
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LEADER IN THE ROOM:
  Name  : {name}
  Role  : {role}
  Depth : {depth}
  Tone  : {tone}
  Must always see : {always_include}
  Must never see  : {never_include}
  Max slides      : {max_slides}
  Preferred flow  :
{structure}

{template_context}

RAW CONTENT AVAILABLE:
{content_summary}

{user_instructions_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THINKING STEPS (do these mentally, then output JSON):
  1. What is the ONE core message for {name}?
  2. What is the emotional arc? (awareness → urgency → confidence → action)
  3. Which 3 data points from the content hit hardest for {name}?
  4. What opening hook will make {name} lean forward in the first 10 seconds?
  5. What exact ask will close the deck?
  6. Run the quality control checklist above.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return this exact JSON structure:
{{
  "core_message": "ONE sentence — the single belief {name} must leave with",
  "opening_hook": "SPECIFIC hook for {name} — not generic. Quote a number or a pain.",
  "emotional_arc": "from [current state] → [tension] → [solution insight] → [future state with ask]",
  "power_data_points": [
    "strongest number for {name} with context",
    "second strongest",
    "third strongest"
  ],
  "closing_ask": "exact decision/action/approval needed from {name} — with ₹ amount or scope",
  "slide_plan": [
    {{
      "slide_number": 1,
      "slide_type": "title",
      "title": "deck title — max 8 words, lead with the insight",
      "purpose": "what question does this slide answer?",
      "lead_with": "the most important element on this slide",
      "has_chart": false,
      "has_diagram": false,
      "notes": "what the presenter says — context NOT shown on slide"
    }}
  ]
}}

slide_type options: title | executive_summary | content | chart | diagram | comparison | ask

STRICT RULES:
  • Generate EXACTLY {max_slides} slides — not one fewer, not one more. This is mandatory.
  • If content feels thin, expand context, add evidence, or split a point across two slides.
  • NEVER include: {never_include}
  • Last slide MUST be type "ask"
  • has_chart=true ONLY when numeric/trend data is available in RAW CONTENT
  • has_diagram=true ONLY for architecture, flow, journey, or timeline content
  • Title slide: use "title" type, subtitle = presenter name + date
  • Ask slide: title must be the exact decision needed, not "Questions?" or "Thank You"
"""


# ═══════════════════════════════════════════════════════════════════════════════
#  GENERATION CALL — User Prompt
# ═══════════════════════════════════════════════════════════════════════════════

GENERATION_PROMPT = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GENERATION REQUEST — Write every slide
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LEADER: {name} ({role})

NARRATIVE STRATEGY (bake this into EVERY slide):
  Core message   : {core_message}
  Opening hook   : {opening_hook}
  Emotional arc  : {emotional_arc}
  Power data     : {power_data_points}
  Closing ask    : {closing_ask}

WRITING RULES FOR {name}:
  Tone           : {tone}
  Max bullets    : {max_bullets} per slide (HARD LIMIT — cut ruthlessly)
  Max chars/bullet: {max_chars} characters (shorter = better)
  Font minimum   : {min_font}pt → SHORT punchy text only
  Number format  : Indian — ₹, lakhs, crores. Never "million" or "billion".
  Bullet rule    : Start with the INSIGHT, not the setup.
                   ✗ "We implemented caching and saw improvements"
                   ✓ "Caching cut API latency 7x — from 320ms to 45ms"
  Title rule     : Title = the FINDING. Topic titles are forbidden.
                   ✗ "Q3 Revenue"  ✓ "Q3 Revenue +23% — SME Segment Led"
  Key callout    : ONE standout number or fact per slide (or empty string).
                   This becomes the KEY INSIGHT line at the bottom.
  Speaker notes  : 2-3 sentences the presenter speaks out loud.
                   This carries context and subtext NOT shown on the slide.

ALL AVAILABLE CONTENT (use ONLY this — do NOT invent):
{content_str}

SLIDE PLAN (generate content for ALL slides in this exact order):
{slide_plan_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return a JSON ARRAY — one object per slide, SAME ORDER as the plan:
[
  {{
    "slide_number": 1,
    "slide_type": "title",
    "title": "8 words max — lead with the insight",
    "subtitle": "one-liner tagline or presenter/date for title slide — else empty string",
    "bullets": [],
    "key_callout": "standout number or empty string",
    "speaker_notes": "2-3 sentences spoken, not shown",
    "chart_spec": null,
    "diagram_spec": null
  }}
]

chart_spec (use when has_chart=true in plan):
{{
  "type": "bar|line|pie|horizontal_bar",
  "title": "chart title",
  "data": {{
    "labels": ["label1", "label2"],
    "datasets": [{{"label": "series", "values": [100, 200]}}]
  }}
}}

diagram_spec (use when has_diagram=true in plan):
{{
  "type": "architecture|flowchart|comparison|timeline",
  "title": "diagram title",
  "elements": [{{"id": "n1", "label": "Label", "type": "box|diamond|circle", "group": "blue|orange|green|red"}}],
  "connections": [{{"from": "n1", "to": "n2", "label": "optional edge label"}}]
}}

FINAL CHECK before outputting:
  ☐ Array has EXACTLY {slide_count} objects — count them before outputting
  ☐ Every title reveals the insight (no topic-only titles)
  ☐ All bullets start with the insight, not the setup
  ☐ Numbers are real (from content above) — never invented
  ☐ Narrative flows: each slide connects to the next
  ☐ Ask slide has specific decision + ₹ amount or scope
  ☐ No content that {name} "never wants" is in any slide
  ☐ JSON is valid — no trailing commas, no unquoted strings
"""


# ═══════════════════════════════════════════════════════════════════════════════
#  AGENT CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class PPTAgent:
    """
    Two-call agent:
      plan()         → Call 1: narrative strategy (returns slide plan for UI review)
      generate_all() → Call 2: full slide content (all slides in one coherent pass)
    """

    def __init__(self, claude_client: ClaudeClient):
        self.claude = claude_client
        self._last_strategy: dict = {}

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    def plan(self, content: dict, profile: dict, user_instructions: str = "") -> list:
        """
        Call 1 — Strategy. Returns a slide plan list for the app.py review UI.
        user_instructions: any extra context the user typed in the UI tabs.
        """
        prefs  = profile["content_preferences"]
        vis    = profile["visual_preferences"]
        tone   = profile["tone"]

        template_ctx = self._read_template(_DEFAULT_TEMPLATE)
        content_summary = self._summarize_content(content)

        instructions_block = (
            f"\nADDITIONAL CONTEXT FROM USER (takes highest priority):\n"
            f"{user_instructions.strip()}\n"
            f"→ Adjust the entire narrative strategy to honour these instructions.\n"
            if user_instructions.strip() else ""
        )

        prompt = STRATEGY_PROMPT.format(
            name=profile["name"],
            role=profile["role"],
            depth=prefs["depth"],
            tone=tone["language"],
            always_include=", ".join(tone.get("always_include", [])),
            never_include=", ".join(tone.get("never_include", [])),
            max_slides=prefs["max_slides"],
            structure="\n".join(f"    - {s}" for s in profile.get("structure", [])),
            content_summary=content_summary,
            template_context=template_ctx,
            user_instructions_block=instructions_block,
        )

        strategy = self.claude.generate_json(STRATEGY_SYSTEM, prompt, max_tokens=4096)
        self._last_strategy = strategy

        slides = strategy.get("slide_plan", [])

        # Normalise fields so the app.py review UI works unchanged
        layout_map = {
            "title":             "title_slide",
            "executive_summary": "bullets_with_callout",
            "chart":             "chart_with_text",
            "diagram":           "diagram_full",
            "comparison":        "two_column",
            "ask":               "ask_slide",
            "content":           "bullets",
        }
        for slide in slides:
            slide.setdefault("layout",          layout_map.get(slide.get("slide_type", "content"), "bullets"))
            slide.setdefault("key_message",     slide.get("lead_with", slide.get("purpose", "")))
            slide.setdefault("content_source",  "")
            slide.setdefault("bullets_planned", vis["max_bullet_points_per_slide"])
            slide.setdefault("subtitle",        "")
            slide.setdefault("diagram_type",    None)

        return slides[: prefs["max_slides"]]

    def generate_all(self, plan: list, content: dict, profile: dict) -> list:
        """
        Call 2 — Generation. ALL slides in one coherent pass using the strategy
        from Call 1 so narrative flows across the entire deck.
        """
        vis      = profile["visual_preferences"]
        tone     = profile["tone"]
        strategy = self._last_strategy

        prompt = GENERATION_PROMPT.format(
            name=profile["name"],
            role=profile["role"],
            core_message=strategy.get("core_message", ""),
            opening_hook=strategy.get("opening_hook", ""),
            emotional_arc=strategy.get("emotional_arc", ""),
            closing_ask=strategy.get("closing_ask", ""),
            power_data_points=", ".join(strategy.get("power_data_points", [])),
            tone=tone["language"],
            max_bullets=vis["max_bullet_points_per_slide"],
            max_chars=vis.get("max_chars_per_bullet", 70),
            min_font=vis["font_size_minimum"],
            content_str=self._format_content_full(content),
            slide_plan_str=json.dumps(plan, indent=2),
            slide_count=len(plan),
        )

        result = self.claude.generate_json(GENERATION_SYSTEM, prompt, max_tokens=16384)

        slides = result if isinstance(result, list) else result.get("slides", [])

        for i, slide in enumerate(slides):
            plan_item = plan[i] if i < len(plan) else {}
            for key in ["title", "subtitle", "key_callout", "speaker_notes"]:
                slide.setdefault(key, "")
            slide.setdefault("bullets", [])
            slide["slide_number"] = plan_item.get("slide_number", i + 1)
            slide["slide_type"]   = slide.get("slide_type") or plan_item.get("slide_type", "content")
            slide["layout"]       = slide.get("layout")     or plan_item.get("layout", "bullets")

        return slides

    # ── HELPERS ───────────────────────────────────────────────────────────────

    def _read_template(self, template_path: str) -> str:
        """Extract layout names from the Indiamart template for context."""
        try:
            from pptx import Presentation
            prs = Presentation(template_path)
            layout_names = [layout.name for layout in prs.slide_layouts]
            return (
                f"INDIAMART TEMPLATE LAYOUTS AVAILABLE:\n"
                f"  {', '.join(layout_names[:12])}\n"
                f"  Slide size: {prs.slide_width.inches:.1f}\" × {prs.slide_height.inches:.1f}\"\n"
                f"  → Design comes entirely from this template. Content slides use Blank layout.\n"
                f"    Title slide uses the 'Title Slide' layout (first page Indiamart design)."
            )
        except Exception:
            return (
                "TEMPLATE: indiamart_default.pptx (Indiamart brand — orange accent, navy headings, white bg)\n"
                "  Content slides: Blank layout. Title slide: Title Slide layout."
            )

    def _summarize_content(self, content: dict) -> str:
        parts = []
        if content.get("title_suggestion"):
            parts.append(f"Deck topic: {content['title_suggestion']}")
        if content.get("key_metrics"):
            lines = [
                f"  • {m['metric']}: {m['value']} ({m.get('change', '')} {m.get('period', '')})"
                for m in content["key_metrics"][:10]
            ]
            parts.append("Key metrics:\n" + "\n".join(lines))
        for section in ["findings", "achievements", "challenges", "recommendations", "decisions_needed"]:
            items = content.get(section, [])
            if items:
                parts.append(
                    f"{section.replace('_', ' ').title()}:\n"
                    + "\n".join(f"  • {x}" for x in items[:6])
                )
        if content.get("chart_data"):
            parts.append(f"Numeric/chart datasets: {len(content['chart_data'])} available")
        if content.get("diagram_suggestions"):
            parts.append(f"Diagram suggestions: {len(content['diagram_suggestions'])} available")
        return "\n\n".join(parts) if parts else "(No structured content extracted — use any raw text provided)"

    def _format_content_full(self, content: dict) -> str:
        parts = []
        if content.get("key_metrics"):
            parts.append("KEY METRICS:\n" + "\n".join(
                f"- {m['metric']}: {m['value']} (change: {m.get('change', 'N/A')}, period: {m.get('period', '')})"
                for m in content["key_metrics"]
            ))
        for section, label in [
            ("findings",         "FINDINGS"),
            ("achievements",     "ACHIEVEMENTS"),
            ("challenges",       "CHALLENGES"),
            ("recommendations",  "RECOMMENDATIONS"),
            ("decisions_needed", "DECISIONS NEEDED"),
        ]:
            if content.get(section):
                parts.append(f"{label}:\n" + "\n".join(f"- {x}" for x in content[section]))
        if content.get("chart_data"):
            parts.append("CHART DATA:\n" + json.dumps(content["chart_data"], indent=2))
        if content.get("diagram_suggestions"):
            parts.append("DIAGRAM SUGGESTIONS:\n" + json.dumps(content["diagram_suggestions"], indent=2))
        if content.get("raw_text"):
            parts.append(f"RAW TEXT:\n{str(content['raw_text'])[:3000]}")
        return "\n\n".join(parts) if parts else "(No content provided)"

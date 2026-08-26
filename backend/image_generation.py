import os
import requests
import time
import argparse
from typing import Dict, Any

# ==============================================================================
# API Configuration
# ==============================================================================
API_URL = "https://api.vmodel.ai/api/tasks/v1/create"
API_TOKEN = os.getenv(
    "VModel_API_TOKEN",
    "Rb5cf9IwzPrRRqnKW2ctTIT2hDVAWFks4tR1l9T-orhkbFOg3RR0raG0LvhaS2ctAFPwW9xqfdtBTZDDGt3mEQ=="
)

# ==============================================================================
# DYNAMIC PAGE INFORMATION (Edit these values for any webpage/topic)
# ==============================================================================
PAGE_INFO: Dict[str, str] = {
    "page_type": "Service x Industry",
    "page_title": "RAG Chatbot Development for Healthcare",
    "url_slug": "/rag-chatbot-healthcare",
    "primary_keyword": "RAG chatbot for healthcare",
    "secondary_keywords": "medical AI assistant, HIPAA compliant chatbot",
    "search_intent": "Commercial",
    "internal_link_cta": "/services/rag-development",
    "content_angle_notes": "Cover HIPAA, PHI handling, clinical use cases. Real compliance detail, not name-swap."
}

# Image type options:
# - "hero_architecture"   -> Main topic/hero editorial illustration
# - "technical_security"  -> Architecture, security, compliance & core mechanism illustration
# - "workflow_ui"         -> User workflow, developer interaction & practical application illustration
# - "all"                 -> Sequentially generate all 3 images
SELECTED_IMAGE_TYPE = "hero_architecture"


# ==============================================================================
# Fully Dynamic Prompt Generator (AI Conceptualizes Visuals per Topic)
# ==============================================================================
def build_image_prompt(info: Dict[str, str], image_type: str = "hero_architecture") -> str:
    """Dynamically instructs the AI image model to conceptualize an original,

    topic-specific editorial vector illustration without hardcoded visual blueprints.
    """
    title = info.get("page_title", "Technology Solution")
    primary_kw = info.get("primary_keyword", title)
    secondary_kws = info.get("secondary_keywords", "")
    content_notes = info.get("content_angle_notes", "")
    page_type = info.get("page_type", "Technology Service / Guide")
    intent = info.get("search_intent", "Commercial")

    kw_summary = f"{primary_kw}" + (f" ({secondary_kws})" if secondary_kws else "")
    notes_context = f"\n**Context & Key Angle:** {content_notes}" if content_notes else ""

    if image_type == "hero_architecture":
        section_focus = "Hero / Overview illustration that visually communicates the core concept, mechanism, or comparison of this topic"
    elif image_type == "technical_security":
        section_focus = "Technical deep-dive illustration highlighting architecture, security, data integrity, or core mechanisms of this topic"
    elif image_type == "workflow_ui":
        section_focus = "Workflow & practical application illustration showing how users or engineers interact with this solution"
    else:
        section_focus = "Informative section illustration representing this topic"

    return f"""Create a clean, premium editorial-style vector illustration for a professional B2B technology website.

**Page Topic:** {title}
**Primary Focus / Keywords:** {kw_summary}
**Page Type & Intent:** {page_type} ({intent}){notes_context}
**Section Purpose:** {section_focus}

### Visual Concept Guidelines

Create an original, thoughtful visual composition tailored specifically to **"{title}"**:
* Dynamically visualize the key entities, systems, workflows, or comparisons implied by the topic and notes.
* If this is a comparison or decision guide (e.g. between frameworks, tools, or approaches), visually illustrate the two concepts, evaluation trade-offs, or integration ecosystems side-by-side.
* If this is a technical service or system, visually illustrate the underlying pipeline, intelligence engine, and real-world value.
* Use clean geometric containers, modular cards, subtle node connections, and abstract icons to tell the visual story naturally.

### Visual Style

* Modern flat vector illustration with a minimal editorial infographic aesthetic
* Professional SaaS / B2B technology website style (clean, modern, understated)
* Clean geometric shapes with thin dark navy outlines
* Soft, restrained color palette: pastel blue, muted teal, pale green, warm beige, and subtle warm accents
* Very light off-white / ivory background with gentle, subtle depth and rounded corners
* Any human figures should be simple, professional, and naturally proportioned
* Visually informative, balanced, and spacious without clutter or complex code blocks

### Brand & Content Guardrails

* Communicate: clarity, modern engineering excellence, trust, and practical technical depth.
* Do NOT use: generic sci-fi robots, humanoid figures with robotic parts, cyberpunk neon lasers, glowing holographic effects, generic glowing brains, stock-photo realism, or 3D glossy plastic renders.
* No large textual labels or unreadable text inside the illustration; communicate the idea purely through elegant visual symbols, metaphors, and clean structural layout.

### Composition

Wide landscape website illustration (approximately 16:9 aspect ratio) with generous negative space around edges.""".strip()


# ==============================================================================
# API Task Runner
# ==============================================================================
def generate_image_task(prompt_text: str, aspect_ratio: str = "16:9") -> str:
    """Submits the image generation task to VModel API and polls until completion."""
    payload = {
        "version": "3fdd8dc68ca68be11df2e56053a0448f94a94099808a1d61be42a7e86c6ca107",
        "input": {
            "prompt": prompt_text,
            "output_format": "jpg",
            "img_urls": [],
            "aspect_ratio": aspect_ratio,
            "google_search": False
        }
    }

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    print("\n" + "="*70)
    print("SUBMITTING PROMPT TO IMAGE MODEL:")
    print("="*70)
    print(prompt_text)
    print("="*70)

    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"Error submitting task (status {response.status_code}):", response.text)
        return ""

    res_data = response.json()
    if "result" not in res_data or "task_id" not in res_data["result"]:
        print("Unexpected response:", res_data)
        return ""

    task_id = res_data["result"]["task_id"]
    print(f"Task ID: {task_id}")
    print("Generating image (polling status)...", end="", flush=True)

    while True:
        poll_resp = requests.get(
            f"https://api.vmodel.ai/api/tasks/v1/get/{task_id}",
            headers=headers
        )

        data = poll_resp.json()
        result = data.get("result", {})
        status = result.get("status")

        print(f" [{status}]", end="", flush=True)

        if status == "succeeded":
            image_url = result["output"][0]
            print(f"\n\n>>> SUCCESS! Image URL:\n{image_url}\n")
            return image_url

        elif status == "failed":
            print(f"\n\n>>> Generation failed: {result.get('error')}\n")
            return ""

        time.sleep(3)


# ==============================================================================
# Main Runner with CLI & Dictionary Support
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Editorial Vector Image Generator for Webpages")
    parser.add_argument("--type", choices=["hero_architecture", "technical_security", "workflow_ui", "all"], default=None, help="Image type to generate")
    parser.add_argument("--page_title", default=None, help="Page Title (H1)")
    parser.add_argument("--page_type", default=None, help="Page Type")
    parser.add_argument("--primary_kw", default=None, help="Primary Keyword")
    parser.add_argument("--secondary_kw", default=None, help="Secondary Keywords")
    parser.add_argument("--intent", default=None, help="Search Intent")
    parser.add_argument("--notes", default=None, help="Content Angle / Notes")
    parser.add_argument("--aspect_ratio", default="16:9", help="Image aspect ratio (e.g. 16:9, 1:1, 4:3)")

    args = parser.parse_args()

    # If CLI arguments were specified, construct clean configuration without leaking PAGE_INFO
    if args.page_title is not None or args.primary_kw is not None:
        active_info = {
            "page_type": args.page_type or "Technology Solution",
            "page_title": args.page_title or args.primary_kw or "AI Technology Architecture",
            "primary_keyword": args.primary_kw or args.page_title or "",
            "secondary_keywords": args.secondary_kw or "",
            "search_intent": args.intent or "Commercial",
            "content_angle_notes": args.notes or ""
        }
    else:
        active_info = PAGE_INFO.copy()

    selected_type = args.type or SELECTED_IMAGE_TYPE

    print("\n--- ACTIVE PAGE CONFIGURATION ---")
    for k, v in active_info.items():
        print(f"  {k:20}: {v}")
    print(f"  {'image_type':20}: {selected_type}")
    print(f"  {'aspect_ratio':20}: {args.aspect_ratio}")
    print("--------------------------------\n")

    types_to_generate = ["hero_architecture", "technical_security", "workflow_ui"] if selected_type == "all" else [selected_type]

    results = {}
    for img_type in types_to_generate:
        print(f"\n>>> Generating Image for type: [{img_type}]")
        built_prompt = build_image_prompt(active_info, image_type=img_type)
        url = generate_image_task(built_prompt, aspect_ratio=args.aspect_ratio)
        results[img_type] = url

    print("\n" + "="*70)
    print("ALL GENERATIONS COMPLETED:")
    print("="*70)
    for img_type, url in results.items():
        print(f"[{img_type}]:\n  {url if url else 'FAILED'}\n")


if __name__ == "__main__":
    main()
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
def build_image_prompt(info: Dict[str, str], image_type: str = "hero_architecture", aspect_ratio: str = "1:1") -> str:
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

    if image_type in ("hero_architecture", "overview_concept"):
        section_focus = "Visual overview illustration that conceptually communicates the core idea, value, or topic context"
    elif image_type == "technical_security":
        section_focus = "Technical deep-dive illustration highlighting security, compliance, reliability, or mechanisms"
    elif image_type == "workflow_ui":
        section_focus = "Practical application illustration showing real-world utility and user/engineer interaction"
    else:
        section_focus = "Informative editorial illustration representing this topic"

    if aspect_ratio == "1:1":
        composition_instructions = """* Target Aspect Ratio: 1:1 (Square canvas).
* Full Space Utilization: Maximize and fill all available vertical and horizontal space across the square canvas. Arrange the visual entities, cards, and conceptual elements into a well-balanced, multi-tier composition that naturally occupies the full square area. Do NOT generate a narrow horizontal rectangle floating in the middle with huge empty bars on top and bottom."""
    else:
        composition_instructions = f"""* Target Aspect Ratio: {aspect_ratio}.
* Full Space Utilization: Utilize all available canvas space across the {aspect_ratio} frame with a balanced, edge-to-edge distribution of visual elements."""

    return f"""Create a clean, premium editorial-style vector illustration for a professional B2B technology website.

**Page Topic:** {title}
**Primary Focus / Keywords:** {kw_summary}
**Page Type & Intent:** {page_type} ({intent}){notes_context}
**Section Purpose:** {section_focus}

### Canvas & Space Utilization
{composition_instructions}
* Use all available space in the image in the selected {aspect_ratio} ratio with an engaging, well-distributed layout.

### Visual Concept Guidelines

Create an original, thoughtful visual composition tailored specifically to **"{title}"**:
* Conceptually visualize the central theme, key entities, trade-offs, or real-world value of this topic.
* If this is a comparison or decision guide, visually balance the two concepts, evaluation criteria, or trade-offs side-by-side or in a comparative matrix.
* If this is a service, technology, or glossary guide, creatively visualize the core solution, domain benefits, and practical execution.
* Use clean minimalist visual symbols, modular cards, abstract shapes, and subtle decorative accents to tell the visual story naturally.
* STRICT CONTAINER RULE: Do NOT create any large enclosing container, outer panel, background box, surrounding frame, dashboard window, or large rounded rectangle around the central content. Place individual visual elements and cards directly onto the open canvas with clean whitespace between them. Only the individual micro-cards/components should have their own borders.

### Visual Style

* Modern flat vector illustration with a minimal editorial infographic aesthetic
* Professional SaaS / B2B technology website style (clean, modern, understated)
* Clean geometric shapes with thin dark navy outlines
* Soft, restrained color palette: pastel blue, muted teal, pale green, warm beige, and subtle warm accents
* Clean, solid off-white / light background with NO outer frames, NO surrounding borders, and NO enclosing boxes
* Any human figures should be simple, professional, and naturally proportioned
* Visually informative, balanced, and spacious without clutter or complex code blocks

### Brand & Content Guardrails

* Communicate: clarity, modern engineering excellence, trust, and practical technical depth.
* STRICTLY PROHIBITED: Do NOT draw any outer container box, enclosing panel, window frame, browser mockup, or background bounding box around the composition.
* Do NOT use: generic sci-fi robots, humanoid figures with robotic parts, cyberpunk neon lasers, glowing holographic effects, generic glowing brains, stock-photo realism, or 3D glossy plastic renders.
* Do NOT force repetitive flowcharts or database cylinders unless explicitly required by the topic itself.
* No large textual labels or unreadable text inside the illustration; communicate the idea purely through elegant visual symbols, metaphors, and clean structural layout.
""".strip()


# ==============================================================================
# API Task Runner
# ==============================================================================
def generate_image_task(prompt_text: str, aspect_ratio: str = "1:1") -> str:
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
# Pipeline-callable helpers: download + generate for a placeholder
# ==============================================================================
def download_image(image_url: str, save_path: str) -> str:
    """Download an image from a URL and save it to a local path. Returns the save path on success, empty string on failure."""
    try:
        resp = requests.get(image_url, timeout=120, stream=True)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  [IMG] Downloaded -> {save_path}")
        return save_path
    except Exception as e:
        print(f"  [IMG ERROR] Failed to download {image_url}: {e}")
        return ""


def generate_for_placeholder(
    page_title: str,
    page_type: str = "Technology Solution",
    primary_keyword: str = "",
    secondary_keywords: str = "",
    content_angle_notes: str = "",
    section_context: str = "",
    image_type: str = "hero_architecture",
    aspect_ratio: str = "1:1",
    save_path: str = "",
) -> str:
    """
    Generate an image for a specific placeholder and download it locally.

    Args:
        page_title: The page's H1 / title.
        page_type: Page archetype (Comparison, Service x Industry, etc.).
        primary_keyword: Primary SEO keyword.
        secondary_keywords: Secondary keywords.
        content_angle_notes: Content angle / notes for differentiation.
        section_context: Extra context extracted from the section (h2 text, eyebrow, etc.).
        image_type: One of hero_architecture, technical_security, workflow_ui.
        aspect_ratio: Target aspect ratio string (e.g. "1:1", "16:9").
        save_path: Full local file path where the image should be saved.

    Returns:
        The local file path on success, empty string on failure.
    """
    info = {
        "page_type": page_type,
        "page_title": page_title,
        "primary_keyword": primary_keyword or page_title,
        "secondary_keywords": secondary_keywords,
        "search_intent": "Commercial",
        "content_angle_notes": content_angle_notes,
    }

    # Append section-specific context to content notes for more relevant imagery
    if section_context:
        info["content_angle_notes"] = (
            (info["content_angle_notes"] + " | " if info["content_angle_notes"] else "")
            + f"Section context: {section_context}"
        )

    prompt = build_image_prompt(info, image_type=image_type, aspect_ratio=aspect_ratio)
    image_url = generate_image_task(prompt, aspect_ratio=aspect_ratio)

    if not image_url:
        print(f"  [IMG ERROR] Image generation returned no URL for section: {section_context[:60]}...")
        return ""

    if not save_path:
        # Default fallback path
        import re as _re
        slug = _re.sub(r"[^\w\-]+", "-", page_title.lower()).strip("-")
        save_path = os.path.join(os.path.dirname(__file__), "generated_images", f"{slug}-{image_type}.jpg")

    return download_image(image_url, save_path)


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
    parser.add_argument("--aspect_ratio", default="1:1", help="Image aspect ratio (e.g. 16:9, 1:1, 4:3)")

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
        built_prompt = build_image_prompt(active_info, image_type=img_type, aspect_ratio=args.aspect_ratio)
        url = generate_image_task(built_prompt, aspect_ratio=args.aspect_ratio)
        results[img_type] = url

    print("\n" + "="*70)
    print("ALL GENERATIONS COMPLETED:")
    print("="*70)
    for img_type, url in results.items():
        print(f"[{img_type}]:\n  {url if url else 'FAILED'}\n")


if __name__ == "__main__":
    main()
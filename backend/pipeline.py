"""
Full Website Generation Pipeline
=================================
Reads actual_data + rules for each section, sends them to an LLM via OpenRouter
tailored to the target Page Title, Page Type, Primary Keyword, Secondary Keyword,
and Content Angle / Notes, stores generated JSON in generated/, then compiles
the final HTML page.

Usage:
  python pipeline.py --page-title "LangChain vs LlamaIndex Development Services" \
                     --page-type "Comparison" \
                     --primary-keyword "LangChain vs LlamaIndex" \
                     --secondary-keyword "RAG framework comparison, LLM orchestration" \
                     --content-angle "Hands-on engineering comparison between LangGraph multi-step agents vs LlamaIndex retrieval quality, plus hybrid architecture in 2026."
"""

import os
import re
import sys
import json
import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure UTF-8 output formatting on Windows CMD/PowerShell
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── dependency bootstrap ──────────────────────────────────────────────────────
from litellm import completion

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("beautifulsoup4 not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)

# Viewer widget generation & injection modules
from generate_viwer import generate_viewer
from inject_viewer import inject_widget_into_html

# Image generation module (for placeholder replacement)
from image_generation import generate_for_placeholder

# Generated images output directory
GENERATED_IMAGES_DIR = os.path.join(BASE_DIR, "generated_images")
os.makedirs(GENERATED_IMAGES_DIR, exist_ok=True)

# ── paths ─────────────────────────────────────────────────────────────────────
IS_VERCEL = "VERCEL" in os.environ or "AWS_LAMBDA_FUNCTION_NAME" in os.environ

PAGE_TYPES_DIR = os.path.join(BASE_DIR, "page_types")
DEFAULT_TYPE_DIR = os.path.join(PAGE_TYPES_DIR, "comparison")

if IS_VERCEL:
    import tempfile
    WORK_TMP = tempfile.gettempdir()
    HTML_PAGES_DIR = os.path.join(WORK_TMP, "HTML pages")
else:
    HTML_PAGES_DIR = os.path.join(BASE_DIR, "HTML pages")

ACTUAL_DATA_DIR = os.path.join(DEFAULT_TYPE_DIR, "actual_data")
RULES_DIR = os.path.join(DEFAULT_TYPE_DIR, "rules")
GENERATED_DIR = os.path.join(DEFAULT_TYPE_DIR, "generated")

os.makedirs(HTML_PAGES_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

def get_page_type_dirs(page_type="Comparison"):
    """
    Resolve (actual_data_dir, rules_dir, generated_dir) based on page_type.
    Falls back to 'comparison' folder if specific page_type folder is not present.
    """
    import re
    slug = page_type.lower().replace(" ", "_").replace("/", "_").replace("-", "_") if page_type else "comparison"
    norm_slug = re.sub(r'_+', '_', slug).strip('_')

    target_dir = None
    if os.path.exists(PAGE_TYPES_DIR):
        for name in os.listdir(PAGE_TYPES_DIR):
            norm_name = re.sub(r'_+', '_', name.lower()).strip('_')
            if norm_name == norm_slug:
                target_dir = os.path.join(PAGE_TYPES_DIR, name)
                break
            elif ("tech" in norm_slug or "integration" in norm_slug) and ("tech" in norm_name or "integration" in norm_name):
                target_dir = os.path.join(PAGE_TYPES_DIR, name)
                break
            elif ("glossary" in norm_slug or "defina" in norm_slug or "defini" in norm_slug) and "glossary" in norm_name:
                target_dir = os.path.join(PAGE_TYPES_DIR, name)
                break
            elif ("hire" in norm_slug or "role" in norm_slug) and "hire" in norm_name:
                target_dir = os.path.join(PAGE_TYPES_DIR, name)
                break
            elif ("service" in norm_slug or "industry" in norm_slug) and "service" in norm_name:
                target_dir = os.path.join(PAGE_TYPES_DIR, name)
                break

    if not target_dir or not os.path.exists(target_dir):
        target_dir = DEFAULT_TYPE_DIR

    actual_data_dir = os.path.join(target_dir, "actual_data")
    rules_dir = os.path.join(target_dir, "rules")
    generated_dir = os.path.join(target_dir, "generated")

    os.makedirs(generated_dir, exist_ok=True)
    return actual_data_dir, rules_dir, generated_dir

# Maps page-type slugs → page_types/ directory name
TEMPLATE_DIR_MAP = {
    "comparison": "comparison",
    "technology_integration": "technology_integration",
    "technology___integration": "technology_integration",
    "hire_a_role": "hire_a_role",
    "glossary_definition": "glossary_definition",
    "glossary_defination": "glossary_definition",
    "glossary___definition": "glossary_definition",
    "service_x_industry": "service_x_industry",
    "service_x_industries": "service_x_industry",
    "editorial_blog": "comparison",
}

def get_template_path(page_type="Comparison"):
    """Select the base HTML template from page_types/<archetype>/template.html."""
    slug = (
        page_type.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
        .replace("(", "_")
        .replace(")", "_")
    ) if page_type else "comparison"

    archetype_dir = TEMPLATE_DIR_MAP.get(slug)
    if not archetype_dir:
        if "glossary" in slug or "defina" in slug or "defini" in slug:
            archetype_dir = "glossary_definition"
        elif "role" in slug or "hire" in slug:
            archetype_dir = "hire_a_role"
        elif "service" in slug or "industry" in slug:
            archetype_dir = "service_x_industry"
        elif "tech" in slug or "integration" in slug:
            archetype_dir = "technology_integration"
        else:
            archetype_dir = "comparison"

    # Primary: look for template.html inside page_types/<archetype>/
    cand = os.path.join(PAGE_TYPES_DIR, archetype_dir, "template.html")
    if os.path.exists(cand):
        return cand

    # Fallback: case-insensitive directory scan (handles service_x_Industry etc.)
    if os.path.exists(PAGE_TYPES_DIR):
        norm = re.sub(r'_+', '_', archetype_dir.lower()).strip('_')
        for name in os.listdir(PAGE_TYPES_DIR):
            if re.sub(r'_+', '_', name.lower()).strip('_') == norm:
                cand = os.path.join(PAGE_TYPES_DIR, name, "template.html")
                if os.path.exists(cand):
                    return cand

    # Last resort: default to comparison template
    return os.path.join(PAGE_TYPES_DIR, "comparison", "template.html")

# The four sections in order — each entry maps:
#   data file name  ->  rules file name  ->  generated output name
SECTIONS = [
    {"name": "Hero Section", "data": "hero.json", "rules": "hero_rules.json", "output": "new_hero.json"},
    {"name": "Value & Quick Answer", "data": "second_hero.json", "rules": "second_hero_rules.json", "output": "new_second_hero.json"},
    {"name": "Services & Breakdown", "data": "third_section.json", "rules": "third_section_rules.json", "output": "new_third_section.json"},
    {"name": "Process, Pricing & FAQ", "data": "final_section.json", "rules": "final_section_rules.json", "output": "new_final_section.json"},
]

# ── .env loader ───────────────────────────────────────────────────────────────
def load_dotenv():
    env_path = os.path.join(ROOT_DIR, ".env")
    if not os.path.exists(env_path):
        env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        os.environ[parts[0].strip()] = parts[1].strip()

# ── LLM content generation ───────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are an expert website content strategist, technical writer, SEO copywriter, and conversion copywriter specializing in high-converting, authoritative technical service and knowledge pages.

Your responsibility is NOT to simply rewrite text.

Your responsibility is to regenerate the website content so it becomes a completely new, authoritative, comprehensive website tailored to the given PAGE TITLE, PAGE TYPE, PRIMARY KEYWORD, SECONDARY KEYWORD, and CONTENT ANGLE / NOTES while strictly preserving the original website JSON structure.

Target Page Types & Focus:
- Service x Industry: Focus on industry-specific pain points, compliance, high-ROI use cases, and concrete deliverables.
- Comparison: Provide an honest, objective breakdown of trade-offs, architecture differences, benchmarks, overhead, and hybrid patterns.
- Glossary / Definition: Clear plain-English conceptual definitions, technical deep dives, architectures, and practical application.
- Hire-a-Role: Highlighting hands-on engineering capabilities, production track record, direct access, and engagement models.
- Technology / Integration: Deep technical orchestration, framework integration, pipelines, and production patterns.
- Editorial Blog (Discover): Insightful analysis, industry perspectives, counter-intuitive findings, and actionable recommendations.

CRITICAL INSTRUCTIONS:
1. Content Angle / Notes is the CRITICAL differentiator that keeps the page out of thin-content territory. You MUST deeply weave this angle, technical nuances, specific realities, and benchmarks into all generated text across all sections.
2. SEO Optimization: Naturally weave the Primary Keyword and Secondary Keywords into headings, paragraphs, bullet points, and metadata without keyword stuffing.
3. Treat every section as an independent business section with its own clear purpose:
   - Hero introduces the core value proposition, key metrics, and direct action.
   - Value / Quick Answer provides the plain-English bottom-line answer and immediate clarity.
   - Comparison / Architecture breaks down factor-by-factor evaluations, code volume, overhead, and hybrid realities.
   - Services / Where it wins outlines concrete offerings, engagement scope, and winning decision criteria.
   - Process / Engagement walks through discovery, milestones, evaluation, and deployment.
   - Pricing & FAQ addresses transparent pricing tiers, common objections, and technical trade-offs.
4. JSON Strictness:
   - Never invent new JSON keys.
   - Never remove existing JSON keys.
   - Never rename keys.
   - Never change nesting or array structures.
   - Only modify string values.
   - Follow every constraint described in the provided Rules JSON.
   - Output must be ONLY valid JSON. No markdown fences. No explanations. No comments.
"""


def generate_section(
    page_title,
    page_type,
    primary_keyword,
    secondary_keyword,
    content_angle,
    model,
    data_path,
    rules_path,
    output_path_json,
    step_num=1,
    total_steps=4,
    section_title="Section"
):
    """Send one section through the LLM and save the result."""
    section_name = os.path.basename(data_path)
    print(f"[STEP {step_num}/{total_steps}] Generating {section_title} for '{page_title}' ({page_type})...")

    with open(data_path, "r", encoding="utf-8") as f:
        original_content = json.load(f)
    with open(rules_path, "r", encoding="utf-8") as f:
        rules_content = json.load(f)

    prompt = f"""
Page Title
{page_title}

Page Type
{page_type}

Primary Keyword(just for knowledge)
{primary_keyword}

Secondary Keyword(just for knowledge, Don't make content according this only.)
{secondary_keyword}

Content Angle / Notes (Crucial Differentiator)
{content_angle}

Original Website JSON
{json.dumps(original_content, indent=2)}

Description Rules JSON
{json.dumps(rules_content, indent=2)}

Return ONLY valid JSON matching the exact original structure.
"""

    try:
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )

        content = response.choices[0].message.content.strip()

        # Clean markdown fences if model ignored response_format
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                content = "\n".join(lines[1:-1])

        new_data = json.loads(content)

        # --- Fix double-encoded JSON responses from LLM ---
        if isinstance(new_data, dict) and len(new_data) == 1:
            only_key = list(new_data.keys())[0]
            only_val = new_data[only_key]
            if isinstance(only_val, str):
                try:
                    unwrapped = json.loads(only_val)
                    if isinstance(unwrapped, dict) and len(unwrapped) > 0:
                        print(f"  [FIX] Unwrapped double-encoded JSON (key was: {repr(only_key)})")
                        new_data = unwrapped
                except (json.JSONDecodeError, ValueError):
                    pass

        if not isinstance(new_data, dict) or not new_data:
            raise ValueError(f"Generated content for {section_title} is not a valid non-empty JSON object.")

        os.makedirs(os.path.dirname(output_path_json) or ".", exist_ok=True)
        with open(output_path_json, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=2)

        print(f"[OK] Step {step_num}/{total_steps} complete: {section_title}")
        return new_data

    except Exception as e:
        print(f"\n  [FATAL ERROR] Step {step_num}/{total_steps} failed: {section_title} ({section_name}): {e}")
        raise RuntimeError(f"Section generation failed for '{section_title}': {e}") from e


# ── Helper stubs (kept for _update_meta_and_jsonld; real helpers are in compilers/shared.py) ──
def _set_text(el, text):
    if el and text is not None:
        el.string = str(text)

def _set_href(el, url):
    if el and url:
        el["href"] = str(url)


# ── Meta & JSON-LD updater ────────────────────────────────────────────────────
def _update_meta_and_jsonld(soup, page_title, page_type, primary_keyword, secondary_keyword, content_angle, hero_data=None, final_data=None):
    """
    Update <title>, <meta> tags, canonical link, and JSON-LD structured data.
    """
    head = soup.find("head")
    if not head:
        return

    # 1. <title>
    title_el = head.find("title")
    meta_title = f"{page_title} | Shreyans Padmani" if not "Shreyans" in page_title else page_title
    if title_el:
        title_el.string = meta_title

    # 2. <meta name="description">
    desc_text = ""
    if hero_data and "hero" in hero_data:
        desc_text = hero_data["hero"].get("hero-sub", "")
    if not desc_text:
        desc_text = f"{page_title}: {content_angle}" if content_angle else page_title

    desc_meta = head.find("meta", attrs={"name": "description"})
    if desc_meta:
        desc_meta["content"] = desc_text

    # 3. <meta name="keywords">
    kw_parts = []
    if primary_keyword:
        kw_parts.append(primary_keyword)
    if secondary_keyword:
        kw_parts.append(secondary_keyword)
    kw_str = ", ".join(kw_parts) if kw_parts else page_title
    kw_meta = head.find("meta", attrs={"name": "keywords"})
    if kw_meta:
        kw_meta["content"] = kw_str

    # 4. OpenGraph & Twitter tags
    slug = re.sub(r"[^\w\-]+", "-", page_title.lower()).strip("-")
    page_url = f"https://shreyans.tech/{slug}"

    def _ensure_meta_tag(attr_key, attr_val, content_val):
        if not content_val:
            return
        tag = head.find("meta", attrs={attr_key: attr_val})
        if tag:
            tag["content"] = content_val
        else:
            new_tag = soup.new_tag("meta", content=content_val)
            new_tag[attr_key] = attr_val
            head.append(new_tag)

    _ensure_meta_tag("property", "og:title", page_title)
    _ensure_meta_tag("name", "twitter:title", page_title)
    _ensure_meta_tag("property", "og:description", desc_text)
    _ensure_meta_tag("name", "twitter:description", desc_text)
    _ensure_meta_tag("property", "og:url", page_url)

    # 5. Canonical link
    canon = head.find("link", rel="canonical")
    if canon:
        canon["href"] = page_url

    # 6. JSON-LD Structured Data
    for script in head.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            ld = json.loads(script.string)
            graph = ld.get("@graph", [])
            for node in graph:
                ntype = node.get("@type", "")
                if ntype == "Service":
                    node["name"] = page_title
                    node["url"] = page_url
                elif ntype == "BreadcrumbList":
                    items = node.get("itemListElement", [])
                    if items and len(items) > 0:
                        items[-1]["name"] = page_title
                        items[-1]["item"] = page_url
                elif ntype == "FAQPage":
                    if final_data and "faq" in final_data and "faq" in final_data["faq"]:
                        faq_list = final_data["faq"]["faq"]
                        new_entities = []
                        for item in faq_list:
                            f_item = item.get("faq-item", item)
                            q = f_item.get("faq-q", "")
                            a = f_item.get("faq-a", "")
                            if q and a:
                                new_entities.append({
                                    "@type": "Question",
                                    "name": q,
                                    "acceptedAnswer": {"@type": "Answer", "text": a}
                                })
                        if new_entities:
                            node["mainEntity"] = new_entities

            script.string = json.dumps(ld, indent=2, ensure_ascii=False)
        except Exception:
            pass

    print("  ✓ Meta tags & JSON-LD structured data updated.")


# ── Compiler registry ─────────────────────────────────────────────────────────
# Maps normalised page-type slug -> compiler module name inside compilers/
_COMPILER_MAP = {
    "comparison":              "compilers.comparison",
    "service_x_industry":      "compilers.service_x_industry",
    "glossary___definition":   "compilers.glossary_definition",
    "glossary_definition":     "compilers.glossary_definition",
    "hire_a_role":             "compilers.hire_a_role",
    "technology___integration":"compilers.technology_integration",
    "technology_integration":  "compilers.technology_integration",
    "editorial_blog__discover_":"compilers.editorial_blog",
    "editorial_blog":          "compilers.editorial_blog",
}

def _get_compiler(page_type):
    """Import and return the right compiler module for the given page type."""
    import importlib
    slug = (
        page_type.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
        .replace("(", "_")
        .replace(")", "_")
    ) if page_type else "comparison"
    module_name = _COMPILER_MAP.get(slug)
    if not module_name:
        # Fuzzy fallback: find any key that starts with the first token
        first_token = slug.split("_")[0]
        for k, v in _COMPILER_MAP.items():
            if k.startswith(first_token):
                module_name = v
                break
    if not module_name:
        print(f"  Warning: No compiler found for page type '{page_type}'. Falling back to comparison.")
        module_name = "compilers.comparison"
    return importlib.import_module(module_name)


# ── HTML compilation ─────────────────────────────────────────────────────────
def compile_html(page_title, page_type, primary_keyword, secondary_keyword, content_angle, output_path):
    """Load all generated JSONs and dispatch to the per-page-type compiler."""
    print(f"\n{'='*60}")
    print(f"  Compiling HTML -> {output_path}")
    print(f"  Title: {page_title}  |  Type: {page_type}")
    print(f"{'='*60}")

    _, _, gen_dir = get_page_type_dirs(page_type)

    def load_json(path, sec_name):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required generated data file missing: {path} ({sec_name})")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and len(data) == 1:
                only_key = list(data.keys())[0]
                only_val = data[only_key]
                if isinstance(only_val, str):
                    try:
                        unwrapped = json.loads(only_val)
                        if isinstance(unwrapped, dict) and len(unwrapped) > 0:
                            data = unwrapped
                    except (json.JSONDecodeError, ValueError):
                        pass
            return data

    hero_data   = load_json(os.path.join(gen_dir, "new_hero.json"), "Hero Section")
    second_data = load_json(os.path.join(gen_dir, "new_second_hero.json"), "Value & Quick Answer")
    third_data  = load_json(os.path.join(gen_dir, "new_third_section.json"), "Services & Breakdown")
    final_data  = load_json(os.path.join(gen_dir, "new_final_section.json"), "Process, Pricing & FAQ")

    if not hero_data:
        raise ValueError("Hero section data is missing or invalid. Cannot compile HTML.")

    template_file = get_template_path(page_type)
    if not os.path.exists(template_file):
        raise FileNotFoundError(f"Template HTML file not found: {template_file}")
    with open(template_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # ── Dispatch to per-page-type compiler ────────────────────────
    compiler = _get_compiler(page_type)
    compiler.apply(soup, hero_data, second_data, third_data, final_data)

    # ── Meta & JSON-LD ───────────────────────────────────────────
    _update_meta_and_jsonld(
        soup, page_title, page_type, primary_keyword, secondary_keyword, content_angle,
        hero_data=hero_data, final_data=final_data
    )

    # ── String cleanup & write ────────────────────────────────────
    html_out = str(soup)
    html_out = html_out.replace("<lineargradient", "<linearGradient").replace("</lineargradient>", "</linearGradient>")
    html_out = html_out.replace("viewbox=", "viewBox=")
    html_out = html_out.replace("{{PAGE_TITLE}}", page_title)
    html_out = html_out.replace("{{PAGE_TYPE}}", page_type)
    html_out = html_out.replace("{{PRIMARY_KEYWORD}}", primary_keyword)
    html_out = html_out.replace("{{SECONDARY_KEYWORD}}", secondary_keyword)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"\n  ✓ Final website written to: {output_path}")


# ── SEO & Open Graph Metadata Generator ───────────────────────────────────────
def generate_meta_and_og(
    page_title: str,
    primary_keyword: str = "",
    secondary_keyword: str = "",
    content_angle: str = "",
    model: str = "openrouter/deepseek/deepseek-v4-flash"
):
    """
    Generate SEO Meta Title, Meta Description, OG Title, and OG Description via LLM,
    and print the results to stdout.
    """
    print(f"\n{'='*60}")
    print("  PHASE 4: Generating SEO & Open Graph Metadata via LLM")
    print(f"{'='*60}")

    system_prompt = """You are an expert SEO specialist, digital copywriter, and metadata strategist.
Your task is to generate compelling, high-converting, and search-optimized metadata for a web page based on the given page details.

You MUST generate the following 4 fields:
1. Meta Title: Highly compelling, search-optimized title (50-60 characters). Include the Primary Keyword naturally near the beginning.
2. Meta Description: Engaging search snippet summary (140-160 characters) with a clear value proposition and call-to-action that maximizes CTR. Include primary and/or secondary keywords naturally.
3. OG Title: Optimized for social sharing (LinkedIn, Twitter/X, Facebook). Punchy, professional, and curiosity-provoking (50-65 characters).
4. OG Description: Optimized for social feed cards (100-150 characters) emphasizing benefits and driving engagement.

Output MUST be ONLY a valid JSON object with exactly these keys:
{
  "meta_title": "...",
  "meta_description": "...",
  "og_title": "...",
  "og_description": "..."
}
Do not output any markdown formatting, no explanations, no text outside the JSON object."""

    user_prompt = f"""Page Title:
{page_title}

Primary Keyword (SEO):
{primary_keyword}

Secondary Keyword(s):
{secondary_keyword}

Content Angle / Notes:
{content_angle}

Return ONLY valid JSON matching the specified format."""

    try:
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=1000
        )

        content = response.choices[0].message.content.strip()

        # Clean markdown fences if model included them
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                content = "\n".join(lines[1:-1]).strip()

        data = json.loads(content)

        # Handle potential single-key double-encoded JSON
        if isinstance(data, dict) and len(data) == 1:
            only_val = list(data.values())[0]
            if isinstance(only_val, str):
                try:
                    unwrapped = json.loads(only_val)
                    if isinstance(unwrapped, dict) and len(unwrapped) > 0:
                        data = unwrapped
                except Exception:
                    pass

        meta_title = data.get("meta_title") or data.get("Meta Title") or ""
        meta_description = data.get("meta_description") or data.get("Meta Description") or ""
        og_title = data.get("og_title") or data.get("OG Title") or ""
        og_description = data.get("og_description") or data.get("OG Description") or ""

        print("\n" + "="*60)
        print("  SEO & OPEN GRAPH METADATA GENERATED")
        print("="*60)
        print(f"  Meta Title       : {meta_title}")
        print(f"  Meta Description : {meta_description}")
        print(f"  OG Title         : {og_title}")
        print(f"  OG Description   : {og_description}")
        print("="*60 + "\n")

        return {
            "meta_title": meta_title,
            "meta_description": meta_description,
            "og_title": og_title,
            "og_description": og_description
        }

    except Exception as e:
        print(f"\n  ⚠ [WARNING] Failed to generate SEO/OG metadata: {e}\n")
        fb_desc = f"{page_title}: {content_angle}" if content_angle else page_title
        return {
            "meta_title": f"{page_title} | Shreyans Padmani" if not "Shreyans" in page_title else page_title,
            "meta_description": fb_desc,
            "og_title": page_title,
            "og_description": fb_desc
        }


def apply_meta_and_og_to_html(output_path: str, meta_data: dict, page_type: str = "Comparison"):
    """
    Injects or updates the generated SEO & OG metadata into the compiled HTML file,
    and writes sidecar JSON files so the frontend and API can always retrieve them.
    """
    if not meta_data or not os.path.exists(output_path):
        return

    meta_title = meta_data.get("meta_title", "")
    meta_description = meta_data.get("meta_description", "")
    og_title = meta_data.get("og_title", "")
    og_description = meta_data.get("og_description", "")

    try:
        with open(output_path, "r", encoding="utf-8") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")
        head = soup.find("head")
        if head:
            # 1. Update <title>
            if meta_title:
                title_tag = head.find("title")
                if title_tag:
                    title_tag.string = meta_title
                else:
                    new_title = soup.new_tag("title")
                    new_title.string = meta_title
                    head.append(new_title)

            def set_meta(attrs, content_val):
                if not content_val:
                    return
                tag = head.find("meta", attrs=attrs)
                if tag:
                    tag["content"] = content_val
                else:
                    new_tag = soup.new_tag("meta", content=content_val, **attrs)
                    head.append(new_tag)

            # 2. Meta description
            if meta_description:
                set_meta({"name": "description"}, meta_description)

            # 3. OG Title & Twitter Title
            if og_title:
                set_meta({"property": "og:title"}, og_title)
                set_meta({"name": "twitter:title"}, og_title)

            # 4. OG Description & Twitter Description
            if og_description:
                set_meta({"property": "og:description"}, og_description)
                set_meta({"name": "twitter:description"}, og_description)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(str(soup))
            print(f"  ✓ SEO & OG metadata tags injected into: {output_path}")

    except Exception as e:
        print(f"  ⚠ Failed to inject SEO/OG metadata into HTML: {e}")

    # Also save sidecar JSON files for API and frontend decomposition
    try:
        sidecar_path = os.path.splitext(output_path)[0] + ".meta.json"
        with open(sidecar_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2)

        filename = os.path.basename(output_path)
        hp_sidecar = os.path.join(HTML_PAGES_DIR, os.path.splitext(filename)[0] + ".meta.json")
        if hp_sidecar != sidecar_path:
            with open(hp_sidecar, "w", encoding="utf-8") as f:
                json.dump(meta_data, f, indent=2)

        _, _, gen_dir = get_page_type_dirs(page_type)
        if os.path.exists(gen_dir):
            with open(os.path.join(gen_dir, "new_meta_and_og.json"), "w", encoding="utf-8") as f:
                json.dump(meta_data, f, indent=2)
    except Exception as e:
        print(f"  ⚠ Could not write meta sidecar JSON: {e}")


# ── main entry point ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Full pipeline: generate content for all sections via LLM, then compile into a final website."
    )
    parser.add_argument("--page-title", "--title", type=str, required=True,
                        help="Target page title (e.g. 'LangChain vs LlamaIndex Development Services').")
    parser.add_argument("--page-type", "--type", type=str, default="Comparison",
                        help="Type of page (Service x Industry, Comparison, Glossary / Definition, Hire-a-Role, Technology / Integration, Editorial Blog (Discover)).")
    parser.add_argument("--primary-keyword", type=str, default="",
                        help="Primary keyword for SEO optimization.")
    parser.add_argument("--secondary-keyword", type=str, default="",
                        help="Secondary keyword(s) for SEO optimization.")
    parser.add_argument("--content-angle", type=str, default="",
                        help="Content Angle / Notes - The key differentiator that keeps the page out of thin-content territory.")
    parser.add_argument("--model", type=str, default="openrouter/deepseek/deepseek-v4-flash",
                        help="OpenRouter model to use for generation.")
    parser.add_argument("--output", type=str, default=None,
                        help="Output HTML filename (default: page-<title-slug>.html).")
    parser.add_argument("--skip-generate", action="store_true",
                        help="Skip LLM generation and only compile HTML from existing generated/ files.")
    parser.add_argument("--skip-widget", action="store_true",
                        help="Skip hero viewer widget generation and injection.")
    parser.add_argument("--skip-images", action="store_true",
                        help="Skip image generation for placeholders.")
    parser.add_argument("--sample-widget", type=str, default=None,
                        help="Filename of a specific widget in widgets/ to use as blueprint.")
    args = parser.parse_args()

    load_dotenv()

    if not os.environ.get("OPENROUTER_API_KEY") and not args.skip_generate:
        print("Error: OPENROUTER_API_KEY not found in environment or .env file.")
        return

    slug = re.sub(r"[^\w\-]+", "-", args.page_title.lower()).strip("-")
    output_html = args.output or f"page-{slug}.html"
    if os.path.isabs(output_html):
        output_path = output_html
    else:
        output_path = os.path.join(HTML_PAGES_DIR, os.path.basename(output_html))

    try:
        # ── Phase 1: Concurrent Content Generation & Hero Viewer Widget ──
        actual_data_dir, rules_dir, gen_dir = get_page_type_dirs(args.page_type)
        tmp_widget_path = os.path.join(BASE_DIR, "generated_components", "interactive_viewer.html")

        if not args.skip_generate or (not args.skip_widget and not os.path.exists(tmp_widget_path)):
            print("\n" + "="*60)
            print("  PHASE 1: Concurrent Content & Widget Generation via LLM")
            print("="*60)

            os.makedirs(gen_dir, exist_ok=True)
            futures = {}

            with ThreadPoolExecutor(max_workers=5) as executor:
                # 1. Schedule all 4 Section LLM Generations in parallel
                if not args.skip_generate:
                    for i, section in enumerate(SECTIONS, 1):
                        data_path = os.path.join(actual_data_dir, section["data"])
                        rules_path = os.path.join(rules_dir, section["rules"])
                        output_path_json = os.path.join(gen_dir, section["output"])

                        if not os.path.exists(data_path):
                            raise FileNotFoundError(f"Section data file missing: {data_path}")
                        if not os.path.exists(rules_path):
                            raise FileNotFoundError(f"Section rules file missing: {rules_path}")

                        sec_title = section.get("name", f"Section {i}")
                        f = executor.submit(
                            generate_section,
                            page_title=args.page_title,
                            page_type=args.page_type,
                            primary_keyword=args.primary_keyword,
                            secondary_keyword=args.secondary_keyword,
                            content_angle=args.content_angle,
                            model=args.model,
                            data_path=data_path,
                            rules_path=rules_path,
                            output_path_json=output_path_json,
                            step_num=i,
                            total_steps=len(SECTIONS),
                            section_title=sec_title
                        )
                        futures[f] = f"Section {i} ({sec_title})"

                # 2. Schedule Hero Viewer Widget LLM Generation in parallel
                if not args.skip_widget and (not args.skip_generate or not os.path.exists(tmp_widget_path)):
                    print("  [DISPATCH] Hero viewer widget generation queued in parallel...")
                    f_w = executor.submit(
                        generate_viewer,
                        page_title          = args.page_title,
                        page_type           = args.page_type,
                        primary_keyword     = args.primary_keyword,
                        secondary_keyword   = args.secondary_keyword,
                        content_angle       = args.content_angle,
                        sample_widget_path  = args.sample_widget,
                        model               = args.model,
                        output_path         = tmp_widget_path,
                    )
                    futures[f_w] = "Hero Interactive Viewer Widget"

                # 3. Track all tasks in real-time — fail fast if any task errors out
                for fut in as_completed(futures):
                    task_label = futures[fut]
                    try:
                        fut.result()
                    except Exception as exc:
                        print(f"\n  [FATAL ERROR] Parallel task '{task_label}' failed: {exc}")
                        # Immediately cancel remaining tasks
                        for other_f in futures:
                            other_f.cancel()
                        raise RuntimeError(f"Concurrent task '{task_label}' failed: {exc}") from exc

            print("\n  ✓ All parallel LLM generation tasks completed successfully.")
        else:
            print("\n  Skipping LLM generation (--skip-generate). Using existing generated/ files.")

        # ── Phase 2: Compile Final HTML Template (< 50ms) ──
        print("\n" + "="*60)
        print("  PHASE 2: Compiling HTML Template")
        print("="*60)

        compile_html(
            page_title=args.page_title,
            page_type=args.page_type,
            primary_keyword=args.primary_keyword,
            secondary_keyword=args.secondary_keyword,
            content_angle=args.content_angle,
            output_path=output_path
        )

        # ── Phase 3: Hero Viewer Widget DOM Injection (< 10ms) ──
        if not args.skip_widget:
            print("\n" + "="*60)
            print("  PHASE 3: Injecting Hero Viewer Widget")
            print("="*60)

            if not os.path.exists(tmp_widget_path):
                raise FileNotFoundError(f"Hero viewer widget file not found: {tmp_widget_path}")

            with open(tmp_widget_path, "r", encoding="utf-8") as f:
                widget_html = f.read()
            with open(output_path, "r", encoding="utf-8") as f:
                page_html = f.read()

            updated_html = inject_widget_into_html(page_html, widget_html)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(updated_html)
            print(f"  ✓ Hero viewer widget injected into: {output_path}")

        # ── Phase 4: Parallel Image Generation, Placeholder Replacement & Metadata ──
        print("\n" + "="*60)
        print("  PHASE 4: Image & SEO/OG Metadata Generation")
        print("="*60)

        # Call LLM to generate Meta Title, Meta Description, OG Title, OG Description
        meta_og_data = generate_meta_and_og(
            page_title=args.page_title,
            primary_keyword=args.primary_keyword,
            secondary_keyword=args.secondary_keyword,
            content_angle=args.content_angle,
            model=args.model,
        )

        if meta_og_data:
            apply_meta_and_og_to_html(output_path, meta_og_data, page_type=args.page_type)

        if not getattr(args, 'skip_images', False):
            print("\n" + "="*60)
            print("  Parallel Image Generation & Placeholder Replacement")
            print("="*60)

            _replace_image_placeholders(
                output_path=output_path,
                page_title=args.page_title,
                page_type=args.page_type,
                primary_keyword=args.primary_keyword,
                secondary_keyword=args.secondary_keyword,
                content_angle=args.content_angle,
            )

            # Re-apply metadata to ensure tags remain present after image placeholder replacement
            if meta_og_data:
                apply_meta_and_og_to_html(output_path, meta_og_data, page_type=args.page_type)
        else:
            print("\n  Skipping image generation (--skip-images).")

        print("\n" + "="*60)
        print(f"  🎉 PIPELINE COMPLETE: Website ready at {output_path}")
        print("="*60)

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"  ❌ [PIPELINE FAILED] Execution aborted due to error:")
        print(f"     {e}")
        print(f"{'='*60}")
        # Clean up partial output file so no broken/failed artifact exists
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
                print(f"  [CLEANUP] Deleted incomplete output file: {output_path}")
            except Exception as rem_err:
                print(f"  [CLEANUP ERROR] Failed to delete {output_path}: {rem_err}")
        sys.exit(1)


# ── Image placeholder replacement engine ──────────────────────────────────────
def _replace_image_placeholders(
    output_path,
    page_title,
    page_type,
    primary_keyword,
    secondary_keyword,
    content_angle,
):
    """
    Scan the compiled HTML for all .img-placeholder elements, generate images
    in parallel via VModel API, download locally, and replace placeholders with <img> tags.
    """
    if not os.path.exists(output_path):
        raise FileNotFoundError(f"Output HTML not found for image placeholder replacement: {output_path}")

    with open(output_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    placeholders = soup.find_all("div", class_="img-placeholder")

    if not placeholders:
        print("  No .img-placeholder elements found — nothing to generate.")
        return

    print(f"  Found {len(placeholders)} image placeholder(s). Preparing parallel generation...")
    slug = re.sub(r"[^\w\-]+", "-", page_title.lower()).strip("-")

    tasks = []
    for idx, placeholder in enumerate(placeholders):
        # 1. Extract aspect ratio
        aspect_ratio = "1:1"
        span = placeholder.find("span")
        if span and span.get_text():
            span_text = span.get_text(strip=True)
            ar_match = re.search(r"\((\d+:\d+)\)", span_text)
            if ar_match:
                aspect_ratio = ar_match.group(1)

        # 2. Extract section context
        section_context_parts = []
        parent_section = placeholder.find_parent("section")
        if parent_section:
            sec_id = parent_section.get("id", "")
            if sec_id:
                section_context_parts.append(f"Section: {sec_id}")
            eyebrow = parent_section.find(class_="eyebrow")
            if eyebrow:
                section_context_parts.append(f"Eyebrow: {eyebrow.get_text(strip=True)}")
            h2 = parent_section.find("h2")
            if h2:
                section_context_parts.append(f"Heading: {h2.get_text(strip=True)}")
        section_context = "; ".join(section_context_parts)

        # 3. Determine image type
        image_type = "hero_architecture"
        context_lower = section_context.lower()
        if any(kw in context_lower for kw in ["security", "compliance", "architecture", "technical"]):
            image_type = "technical_security"
        elif any(kw in context_lower for kw in ["workflow", "process", "how", "step"]):
            image_type = "workflow_ui"

        # 4. Save path
        suffix = f"-{idx + 1}" if len(placeholders) > 1 else ""
        filename = f"{slug}{suffix}-{image_type}.jpg"
        save_path = os.path.join(GENERATED_IMAGES_DIR, filename)

        print(f"  [QUEUE] Placeholder #{idx + 1}: {section_context or '(overview)'} | ratio: {aspect_ratio} | type: {image_type}")

        tasks.append({
            "idx": idx,
            "placeholder": placeholder,
            "aspect_ratio": aspect_ratio,
            "section_context": section_context,
            "image_type": image_type,
            "filename": filename,
            "save_path": save_path,
        })

    # 5. Generate and download all images in parallel
    img_futures = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as img_executor:
        for t in tasks:
            fut = img_executor.submit(
                generate_for_placeholder,
                page_title=page_title,
                page_type=page_type,
                primary_keyword=primary_keyword,
                secondary_keywords=secondary_keyword,
                content_angle_notes=content_angle,
                section_context=t["section_context"],
                image_type=t["image_type"],
                aspect_ratio=t["aspect_ratio"],
                save_path=t["save_path"],
            )
            img_futures[fut] = t

        for fut in as_completed(img_futures):
            t = img_futures[fut]
            try:
                local_path = fut.result()
                if not local_path or not os.path.exists(local_path):
                    raise RuntimeError(f"Image download failed for placeholder #{t['idx'] + 1} ({t['filename']})")
                t["local_path"] = local_path
                print(f"  ✓ Image ready for placeholder #{t['idx'] + 1} -> {local_path}")
            except Exception as exc:
                for other_f in img_futures:
                    other_f.cancel()
                raise RuntimeError(f"Image generation failed for placeholder #{t['idx'] + 1}: {exc}") from exc

    # 6. Replace all placeholder DOM elements with <img> tags
    for t in tasks:
        img_src = f"/generated_images/{t['filename']}"
        alt_text = t["section_context"] or page_title
        img_tag = soup.new_tag(
            "img",
            src=img_src,
            alt=alt_text,
            loading="lazy",
        )
        t["placeholder"].replace_with(img_tag)

    html_out = str(soup)
    html_out = html_out.replace("<lineargradient", "<linearGradient").replace("</lineargradient>", "</linearGradient>")
    html_out = html_out.replace("viewbox=", "viewBox=")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"\n  ✓ All image placeholders replaced in parallel. HTML updated: {output_path}")


if __name__ == "__main__":
    main()

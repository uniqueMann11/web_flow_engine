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

    for meta in head.find_all("meta"):
        prop = meta.get("property") or meta.get("name", "")
        if prop in ("og:title", "twitter:title"):
            meta["content"] = page_title
        elif prop in ("og:description", "twitter:description"):
            meta["content"] = desc_text
        elif prop == "og:url":
            meta["content"] = page_url

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
        # ── Step 1: Generate content for each section ──
        actual_data_dir, rules_dir, gen_dir = get_page_type_dirs(args.page_type)

        if not args.skip_generate:
            print("\n" + "="*60)
            print("  STEP 1: Generating content via LLM")
            print("="*60)

            os.makedirs(gen_dir, exist_ok=True)

            for i, section in enumerate(SECTIONS, 1):
                data_path = os.path.join(actual_data_dir, section["data"])
                rules_path = os.path.join(rules_dir, section["rules"])
                output_path_json = os.path.join(gen_dir, section["output"])

                if not os.path.exists(data_path):
                    raise FileNotFoundError(f"Section data file missing: {data_path}")
                if not os.path.exists(rules_path):
                    raise FileNotFoundError(f"Section rules file missing: {rules_path}")

                sec_title = section.get("name", f"Section {i}")
                generate_section(
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
        else:
            print("\n  Skipping LLM generation (--skip-generate). Using existing generated/ files.")

        # ── Step 2: Compile final HTML ──
        print("\n" + "="*60)
        print("  STEP 2: Compiling HTML")
        print("="*60)

        compile_html(
            page_title=args.page_title,
            page_type=args.page_type,
            primary_keyword=args.primary_keyword,
            secondary_keyword=args.secondary_keyword,
            content_angle=args.content_angle,
            output_path=output_path
        )

        # ── Step 3: Hero Viewer Widget Generation & Injection ──
        if not args.skip_widget:
            print("\n" + "="*60)
            print("  STEP 3: Hero Viewer Widget Generation & Injection")
            print("="*60)

            tmp_widget_path = os.path.join(BASE_DIR, "generated_components", "interactive_viewer.html")

            if not args.skip_generate or not os.path.exists(tmp_widget_path):
                print("  Generating page-specific hero viewer widget via LLM...")
                generate_viewer(
                    page_title          = args.page_title,
                    page_type           = args.page_type,
                    primary_keyword     = args.primary_keyword,
                    secondary_keyword   = args.secondary_keyword,
                    content_angle       = args.content_angle,
                    sample_widget_path  = args.sample_widget,
                    model               = args.model,
                    output_path         = tmp_widget_path,
                )
            else:
                print(f"  Using existing hero widget file: {tmp_widget_path}")

            if not os.path.exists(tmp_widget_path):
                raise FileNotFoundError(f"Hero viewer widget file not generated: {tmp_widget_path}")

            with open(tmp_widget_path, "r", encoding="utf-8") as f:
                widget_html = f.read()
            with open(output_path, "r", encoding="utf-8") as f:
                page_html = f.read()

            updated_html = inject_widget_into_html(page_html, widget_html)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(updated_html)
            print(f"  ✓ Hero viewer widget injected into: {output_path}")

        # ── Step 4: Image Generation & Placeholder Replacement ──
        if not getattr(args, 'skip_images', False):
            print("\n" + "="*60)
            print("  STEP 4: Image Generation & Placeholder Replacement")
            print("="*60)

            _replace_image_placeholders(
                output_path=output_path,
                page_title=args.page_title,
                page_type=args.page_type,
                primary_keyword=args.primary_keyword,
                secondary_keyword=args.secondary_keyword,
                content_angle=args.content_angle,
            )
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
    Scan the compiled HTML for all .img-placeholder elements, generate an image
    for each via VModel API, download locally, and replace the placeholder with
    an <img> tag.
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

    print(f"  Found {len(placeholders)} image placeholder(s). Generating images...")
    slug = re.sub(r"[^\w\-]+", "-", page_title.lower()).strip("-")
    modified = False

    for idx, placeholder in enumerate(placeholders):
        print(f"\n  ── Placeholder {idx + 1}/{len(placeholders)} ──")

        # 1. Extract aspect ratio from the <span> text inside the placeholder
        aspect_ratio = "1:1"  # default
        span = placeholder.find("span")
        if span and span.get_text():
            span_text = span.get_text(strip=True)
            # Look for patterns like (1:1), (16:9), (4:3)
            ar_match = re.search(r"\((\d+:\d+)\)", span_text)
            if ar_match:
                aspect_ratio = ar_match.group(1)
        print(f"     Aspect ratio: {aspect_ratio}")

        # 2. Extract section context from surrounding HTML
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
        print(f"     Context: {section_context or '(none)'}")

        # 3. Determine image type from section context
        image_type = "hero_architecture"  # default
        context_lower = section_context.lower()
        if any(kw in context_lower for kw in ["security", "compliance", "architecture", "technical"]):
            image_type = "technical_security"
        elif any(kw in context_lower for kw in ["workflow", "process", "how", "step"]):
            image_type = "workflow_ui"

        # 4. Build save path
        suffix = f"-{idx + 1}" if len(placeholders) > 1 else ""
        filename = f"{slug}{suffix}-{image_type}.jpg"
        save_path = os.path.join(GENERATED_IMAGES_DIR, filename)

        # 5. Generate and download image
        local_path = generate_for_placeholder(
            page_title=page_title,
            page_type=page_type,
            primary_keyword=primary_keyword,
            secondary_keywords=secondary_keyword,
            content_angle_notes=content_angle,
            section_context=section_context,
            image_type=image_type,
            aspect_ratio=aspect_ratio,
            save_path=save_path,
        )

        if not local_path or not os.path.exists(local_path):
            raise RuntimeError(f"Image generation/download failed for placeholder #{idx + 1} (type: {image_type}, aspect: {aspect_ratio})")

        # 6. Build the <img> tag and replace the placeholder
        img_src = f"/generated_images/{filename}"
        alt_text = section_context or page_title
        img_tag = soup.new_tag(
            "img",
            src=img_src,
            alt=alt_text,
            loading="lazy",
        )

        # Replace the .img-placeholder div with the <img> tag
        placeholder.replace_with(img_tag)
        modified = True
        print(f"     ✓ Placeholder replaced with <img src=\"{img_src}\" />")

    if modified:
        html_out = str(soup)
        # Fix SVG case-sensitivity mangled by BeautifulSoup
        html_out = html_out.replace("<lineargradient", "<linearGradient").replace("</lineargradient>", "</linearGradient>")
        html_out = html_out.replace("viewbox=", "viewBox=")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_out)
        print(f"\n  ✓ All image placeholders processed. HTML updated: {output_path}")


if __name__ == "__main__":
    main()

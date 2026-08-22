"""
Hero Viewer Widget Generator via LLM
=====================================
Generates an interactive, topic- and page-type-specific visual widget
to replace the hero section's interactive viewer.

Examples:
  - Comparison (LangChain vs LlamaIndex) -> Interactive framework fit finder / benchmark toggler
  - Service x Industry (AI for Fintech)  -> Live fraud anomaly scoring / throughput simulator
  - Technology / Integration             -> Interactive agent DAG / state-machine step inspector
  - Glossary / Definition               -> Interactive architecture diagram & latency breakdown

Usage:
  python generate_viwer.py --page-title "LangChain vs LlamaIndex" --page-type "Comparison"
"""

import os
import sys
import glob
import random
import argparse
import subprocess
import re

# Ensure UTF-8 output formatting on Windows CMD/PowerShell
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Load .env automatically
def load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        os.environ[parts[0].strip()] = parts[1].strip()

# Bootstrap LiteLLM
try:
    from litellm import completion
except ImportError:
    print("litellm not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "litellm"])
    from litellm import completion

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Design tokens ───────────────────────────────────────────────────────────
DESIGN_TOKENS = """
:root {
  --ink: #0A1222;
  --ink-soft: #1B2740;
  --body: #48566E;
  --muted: #6B7A93;
  --line: #E6ECF4;
  --line-soft: #EFF3F9;
  --surface: #FFFFFF;
  --soft: #F4F8FD;
  --tint: #EAF0FF;
  --blue: #2456E6;
  --blue-strong: #1740C0;
  --blue-tint: #E6EEFF;
  --violet: #6D5EF6;
  --violet-tint: #EDEAFE;
  --mint: #0FA968;
  --mint-tint: #E4F7EE;
  --mint-deep: #0B7D4E;
  --amber: #D97A18;
  --amber-tint: #FCEFDD;
  --rose: #E11D48;
  --sh-sm: 0 1px 2px rgba(10, 18, 34, .04), 0 2px 6px rgba(10, 18, 34, .05);
  --sh-md: 0 14px 34px -16px rgba(10, 18, 34, .22);
  --sh-lg: 0 30px 70px -28px rgba(36, 86, 230, .32);
  --r: 18px;
  --r-sm: 12px;
  --disp: "Plus Jakarta Sans", system-ui, sans-serif;
  --bodyf: "Inter", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, monospace;
}
"""

SYSTEM_PROMPT = """
You are a senior Frontend Engineer and Creative UI Developer specializing in high-converting, topic-specific hero-section interactive widgets.

Your job is to generate a self-contained, responsive interactive widget that:
  1. Specifically visualizes the given PAGE TITLE, PAGE TYPE, and CONTENT ANGLE.
  2. Offers at least ONE genuine user interaction (e.g. tab toggles, scenario switcher, metric calculator, interactive node inspection, or filter slider) using pure vanilla JavaScript.
  3. Uses CSS custom properties from the provided DESIGN TOKENS.
  4. Is visually stunning, modern, ultra-clean, and fitting for a premium technical personal brand or service website.

DIMENSION & STRUCTURE RULES:
- The widget root element MUST have class `.viewer` or `.vw-card`.
- Width: 100%. Max-width: 520px. Box-sizing: border-box.
- Self-contained HTML component output: begins with `<style>` and includes the markup and `<script>`.
- CRITICAL: Do NOT include `body`, `html`, or `*` selector rules in your CSS! Do NOT set `body { padding: ... }` or `body { display: flex; }`! The widget is an embedded component inside the hero section of an existing page.
- Scope all component styles inside `.viewer` or `.vw-card` and its child classes (e.g., `.viewer .vw-top`, `.viewer button`).
- All design tokens (--ink, --blue, --mint, --surface, --soft, --r, --disp, --mono, etc.) are already defined by the parent page and directly available via CSS variables.
- Do NOT wrap in `<html>`, `<head>`, or `<body>`.
- Do NOT write CSS comments (/* ... */) or HTML comments. Write clean, direct code only.
- Responsive: ensure it looks crisp on mobile screens down to 320px.

OUTPUT RULES:
- Return ONLY the raw HTML component string (with embedded `<style>` and `<script>`).
- No markdown fences (no ```html), no explanations, no extra prose.
"""

def clean_sample_widget_code(raw_code: str) -> str:
    """Extract style, markup, and script from sample widget, stripping html/body wrappers and body styles."""
    style_blocks = re.findall(r"<style[^>]*>(.*?)</style>", raw_code, re.DOTALL | re.IGNORECASE)
    script_blocks = re.findall(r"<script[^>]*>(.*?)</script>", raw_code, re.DOTALL | re.IGNORECASE)

    css = "\n".join(style_blocks)
    # Strip body, html, * rules
    css = re.sub(r'(?:^|(?<=[{};\s]))\s*(?:body|html|\*|:root)\s*\{[^{}]*\}', '', css, flags=re.IGNORECASE)
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL).strip()

    # Extract body content (inside body or div.vw-card / div.viewer)
    body_match = re.search(r'<body[^>]*>(.*?)</body>', raw_code, re.DOTALL | re.IGNORECASE)
    body_content = body_match.group(1).strip() if body_match else raw_code
    # Strip script tags from body_content
    body_content = re.sub(r'<script[^>]*>.*?</script>', '', body_content, flags=re.DOTALL | re.IGNORECASE).strip()

    js = "\n".join(script_blocks).strip()

    parts = []
    if css.strip():
        parts.append(f"<style>\n{css.strip()}\n</style>")
    if body_content.strip():
        parts.append(body_content.strip())
    if js.strip():
        parts.append(f"<script>\n{js.strip()}\n</script>")

    return "\n\n".join(parts)


def get_sample_widgets(widgets_dir: str) -> list:
    pattern = os.path.join(widgets_dir, "*.html")
    all_files = glob.glob(pattern)
    return [f for f in all_files if os.path.basename(f).lower() != "index.html"]


def select_sample_widget(widgets_dir: str, specific_widget: str = None) -> tuple:
    if specific_widget:
        path = os.path.join(widgets_dir, specific_widget)
        if not os.path.exists(path):
            path = specific_widget
        if not os.path.exists(path):
            return None, ""
    else:
        candidates = get_sample_widgets(widgets_dir)
        if not candidates:
            return None, ""
        path = random.choice(candidates)
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    cleaned_code = clean_sample_widget_code(code)
    return os.path.basename(path), cleaned_code


def generate_viewer(
    page_title: str,
    page_type: str = "Comparison",
    primary_keyword: str = "",
    secondary_keyword: str = "",
    content_angle: str = "",
    model: str = "openrouter/deepseek/deepseek-v4-flash",
    output_path: str = "generated_components/interactive_viewer.html",
    sample_widget_path: str = None,
    # Backward-compat args
    role: str = None,
    city: str = None,
    state: str = None,
    **kwargs
):
    actual_title = page_title or role or "Technical Comparison"
    actual_type = page_type or "Comparison"

    print(f"\n{'='*60}")
    print(f"  Generating hero viewer widget via LLM")
    print(f"  Title : {actual_title}")
    print(f"  Type  : {actual_type}")
    print(f"  Model : {model}")
    print(f"{'='*60}\n")

    widgets_dir = os.path.join(BASE_DIR, "widgets")
    sample_name, sample_code = select_sample_widget(widgets_dir, sample_widget_path)

    example_block = ""
    if sample_code:
        example_block = f"""
EXAMPLE BLUEPRINT (Reference for component styling and interaction patterns):
<example>
{sample_code}
</example>
"""

    user_prompt = f"""
Generate an interactive, state-of-the-art hero viewer widget for:

PAGE TITLE     : {actual_title}
PAGE TYPE      : {actual_type}
PRIMARY KEYWORD: {primary_keyword}
SECONDARY KW   : {secondary_keyword}
CONTENT ANGLE  : {content_angle}

DESIGN TOKENS:
{DESIGN_TOKENS}

{example_block}

Requirements:
- Make it highly relevant to "{actual_title}" and the page type "{actual_type}".
- If Comparison: allow toggling between the two frameworks/tools or testing 2-3 project scenarios to see suitability, latency, or code differences.
- If Service x Industry: provide an interactive ROI / latency / throughput calculation or architecture check for that industry.
- If Technology / Integration: provide an interactive pipeline DAG / step inspector.
- Pure vanilla HTML + CSS + JS only. Start directly with <style>.
- Do NOT style `body` or `*`. Scope all CSS inside `.viewer` or `.vw-card`.
- Don't use any emojis. Icons can be used.
"""

    response = completion(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ]
    )

    html = response.choices[0].message.content.strip()

    if html.startswith("```"):
        lines = html.splitlines()
        start = 1 if lines[0].startswith("```") else 0
        end   = -1 if lines[-1].strip() == "```" else len(lines)
        html  = "\n".join(lines[start:end])

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  [OK] Hero viewer widget saved to: {os.path.abspath(output_path)}\n")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate an interactive hero viewer widget using an LLM."
    )
    parser.add_argument("--page-title", "--title", type=str, required=True,
                        help="Page title to theme the widget around.")
    parser.add_argument("--page-type", "--type", type=str, default="Comparison",
                        help="Page type (Comparison, Service x Industry, etc.).")
    parser.add_argument("--primary-keyword", type=str, default="",
                        help="Primary keyword.")
    parser.add_argument("--secondary-keyword", type=str, default="",
                        help="Secondary keyword.")
    parser.add_argument("--content-angle", type=str, default="",
                        help="Content angle / notes.")
    parser.add_argument("--model", type=str, default="openrouter/deepseek/deepseek-v4-flash",
                        help="OpenRouter model.")
    parser.add_argument("--output", type=str, default="generated_components/interactive_viewer.html",
                        help="Output file path.")
    parser.add_argument("--sample-widget", type=str, default=None,
                        help="Optional specific sample widget file.")
    args = parser.parse_args()

    load_dotenv()

    if not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY not set in environment or .env file.")
        sys.exit(1)

    generate_viewer(
        page_title          = args.page_title,
        page_type           = args.page_type,
        primary_keyword     = args.primary_keyword,
        secondary_keyword   = args.secondary_keyword,
        content_angle       = args.content_angle,
        model               = args.model,
        output_path         = args.output,
        sample_widget_path  = args.sample_widget,
    )


if __name__ == "__main__":
    main()

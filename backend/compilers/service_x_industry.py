"""
Service × Industry page-type compiler.
Sections: hero · comply · what-is · vs-agency (table) · services · use-cases · process · when-not · pricing · faq
Template: page_types/service_x_industry/template.html
"""
from .shared import (
    apply_hero, apply_comply, apply_what_is,
    apply_table_section, apply_services,
    apply_card_grid_section, apply_process,
    apply_pricing, apply_faq,
    set_text,
)


def apply(soup, hero_data, second_data, third_data, final_data):
    # ── 1. Hero ──────────────────────────────────────────────────
    if hero_data:
        apply_hero(soup, hero_data)

    # ── 2. Second hero ───────────────────────────────────────────
    if second_data:
        apply_comply(soup, second_data)
        apply_what_is(soup, second_data)

        # vs-agency (consultant vs agency comparison table)
        va_sec = (
            soup.find(id="vs-agency")
            or soup.find("section", class_=lambda c: c and "vs-agency" in c)
        )
        apply_table_section(soup, va_sec, second_data.get("vs-agency"))
        print("  [OK] Second hero & vs-agency section applied.")

    # ── 3. Third section ─────────────────────────────────────────
    if third_data:
        apply_services(soup, third_data)
        use_sec = (
            soup.find(id="use-cases")
            or soup.find(id="solutions")
            or soup.find("section", class_=lambda c: c and ("use-cases" in c or "solutions" in c))
        )
        apply_card_grid_section(soup, use_sec, third_data.get("use-cases", third_data.get("solutions")))
        print("  [OK] Services & use-cases section applied.")

    # ── 4. Final section ─────────────────────────────────────────
    if final_data:
        apply_process(soup, final_data)
        _apply_when_not(soup, final_data)
        apply_pricing(soup, final_data)
        apply_faq(soup, final_data)
        print("  [OK] Final section applied.")


def _apply_when_not(soup, final_data):
    """Amber callout & section header: when NOT to use this service."""
    when_sec = (
        soup.find(id="when-not")
        or soup.find("section", class_=lambda c: c and "when-not" in c)
    )
    if not (when_sec and "when-not" in final_data):
        return
    wn_data = final_data["when-not"]
    sh = wn_data.get("sec-head", {})
    if sh:
        set_text(when_sec.find(class_="eyebrow"), sh.get("eyebrow"))
        set_text(when_sec.find("h2"), sh.get("h2"))

    callout = when_sec.find(class_="callout")
    if callout and "callout" in wn_data:
        c_p = wn_data["callout"].get("p", [])
        if isinstance(c_p, str):
            c_p = [c_p]
        for i, el in enumerate(callout.find_all("p")):
            if i < len(c_p):
                set_text(el, c_p[i])

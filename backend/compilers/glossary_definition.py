"""
Glossary / Definition page-type compiler.
Compiles generated data into the page_types/glossary_definition/template.html template.
"""
from .shared import (
    apply_hero, apply_comply, apply_what_is,
    apply_card_grid_section, apply_table_section,
    apply_services, apply_process,
    apply_pricing, apply_faq,
    set_text, set_href,
)


def _apply_why(soup, final_data):
    """Update the #why section (why businesses need this technology & common applications)."""
    why_sec = soup.find(id="why") or soup.find("section", class_=lambda c: c and "why" in c)
    if not (why_sec and "why" in final_data):
        return

    w_data = final_data["why"]
    sh = w_data.get("sec-head", {})
    set_text(why_sec.find(class_="eyebrow"), sh.get("eyebrow", w_data.get("eyebrow")))
    set_text(why_sec.find("h2"), sh.get("h2", w_data.get("h2")))

    # Update description paragraph in the left column
    left_p = why_sec.select_one(".grid > div:first-child p:not(.eyebrow)")
    if left_p:
        set_text(left_p, sh.get("p", w_data.get("p")))

    # Update the right card with list
    card_box = why_sec.find(class_="card")
    if card_box and "card" in w_data:
        c_dict = w_data["card"]
        set_text(card_box.find(class_="n"), c_dict.get("n"))
        set_text(card_box.find("h3"), c_dict.get("h3"))

        ul_el = card_box.find("ul")
        if ul_el and "ul" in c_dict:
            li_els = ul_el.find_all("li")
            for j, li_txt in enumerate(c_dict["ul"]):
                if j < len(li_els):
                    set_text(li_els[j], li_txt)
                else:
                    new_li = soup.new_tag("li")
                    new_li.string = str(li_txt)
                    ul_el.append(new_li)
            for j in range(len(c_dict["ul"]), len(li_els)):
                li_els[j].decompose()


def apply(soup, hero_data, second_data, third_data, final_data):
    """
    Apply all 4 generated JSON payloads to the Glossary / Definition HTML template.
    """
    # ── 1. Hero ──────────────────────────────────────────────────
    if hero_data:
        apply_hero(soup, hero_data)

    # ── 2. Second hero ───────────────────────────────────────────
    if second_data:
        apply_comply(soup, second_data)
        apply_what_is(soup, second_data)

        if "how-it-works" in second_data:
            how_sec = soup.find(id="how-it-works") or soup.find("section", class_=lambda c: c and "how-it-works" in c)
            apply_card_grid_section(soup, how_sec, second_data["how-it-works"])
        print("  [OK] Second hero section applied.")

    # ── 3. Third section ─────────────────────────────────────────
    if third_data:
        if "comparison" in third_data:
            cmp_sec = soup.find(id="comparison") or soup.find("section", class_=lambda c: c and "comparison" in c)
            apply_table_section(soup, cmp_sec, third_data["comparison"])

        apply_services(soup, third_data)
        print("  [OK] Third section applied.")

    # ── 4. Final section ─────────────────────────────────────────
    if final_data:
        _apply_why(soup, final_data)
        apply_process(soup, final_data)
        apply_pricing(soup, final_data)
        apply_faq(soup, final_data)
        print("  [OK] Final section applied.")

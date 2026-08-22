"""
Editorial Blog (Discover) page-type compiler.
Sections will be defined once the template HTML is created.
"""
from .shared import (
    apply_hero, apply_what_is,
    apply_card_grid_section, apply_faq,
    set_text,
)


def apply(soup, hero_data, second_data, third_data, final_data):
    # ── 1. Hero ──────────────────────────────────────────────────
    if hero_data:
        apply_hero(soup, hero_data)

    # ── 2. Second hero ───────────────────────────────────────────
    if second_data:
        apply_what_is(soup, second_data)
        # TODO: key takeaways / counter-intuitive findings section
        print("  [OK] Second hero section applied.")

    # ── 3. Third section ─────────────────────────────────────────
    if third_data:
        # Article body / sections / key takeaways
        apply_card_grid_section(soup, soup.find(id="article-body"), third_data.get("sections"))
        print("  [OK] Third section applied.")

    # ── 4. Final section ─────────────────────────────────────────
    if final_data:
        # Author bio / related articles / newsletter
        cta_sec = (
            soup.find(id="cta")
            or soup.find("section", class_=lambda c: c and "cta" in c)
        )
        if cta_sec and "cta" in final_data:
            set_text(cta_sec.find("h2"), final_data["cta"].get("h2"))
            set_text(cta_sec.find("p"), final_data["cta"].get("p"))
        apply_faq(soup, final_data)
        print("  ✓ Final section applied.")

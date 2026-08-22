"""
Comparison page-type compiler.
Sections: hero · comply · what-is · comparison (table) · services · where-wins · process · pricing · faq
Template: langchain-vs-llamaindex.html
"""
from .shared import (
    apply_hero, apply_comply, apply_what_is,
    apply_table_section, apply_services,
    apply_card_grid_section, apply_process,
    apply_pricing, apply_faq,
)


def apply(soup, hero_data, second_data, third_data, final_data):
    # ── 1. Hero ──────────────────────────────────────────────────
    if hero_data:
        apply_hero(soup, hero_data)

    # ── 2. Second hero ───────────────────────────────────────────
    if second_data:
        apply_comply(soup, second_data)
        apply_what_is(soup, second_data)

        cmp_sec = (
            soup.find(id="comparison")
            or soup.find("section", class_=lambda c: c and "comparison" in c)
        )
        apply_table_section(soup, cmp_sec, second_data.get("comparison"))
        print("  [OK] Second hero & comparison section applied.")

    # ── 3. Third section ─────────────────────────────────────────
    if third_data:
        apply_services(soup, third_data)
        where_sec = soup.find(id="where-wins") or soup.find("section", class_=lambda c: c and "where-wins" in c)
        apply_card_grid_section(soup, where_sec, third_data.get("where-wins"))
        print("  [OK] Services & where-wins section applied.")

    # ── 4. Final section ─────────────────────────────────────────
    if final_data:
        apply_process(soup, final_data)
        apply_pricing(soup, final_data)
        apply_faq(soup, final_data)
        print("  [OK] Final section applied.")

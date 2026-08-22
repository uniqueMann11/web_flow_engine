"""
Technology / Integration page-type compiler.
Sections will be defined once the template HTML is created.
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
        # TODO: architecture / integration overview section
        arch_sec = (
            soup.find(id="architecture")
            or soup.find("section", class_=lambda c: c and "architecture" in c)
        )
        apply_table_section(soup, arch_sec, second_data.get("architecture"))
        print("  [OK] Second hero & architecture section applied.")

    # ── 3. Third section ─────────────────────────────────────────
    if third_data:
        apply_services(soup, third_data)
        apply_card_grid_section(soup, soup.find(id="features"), third_data.get("features"))
        apply_card_grid_section(soup, soup.find(id="patterns"), third_data.get("patterns"))
        print("  [OK] Third section applied.")

    # ── 4. Final section ─────────────────────────────────────────
    if final_data:
        apply_process(soup, final_data)
        apply_pricing(soup, final_data)
        apply_faq(soup, final_data)
        print("  [OK] Final section applied.")

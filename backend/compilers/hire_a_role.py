"""
Hire-a-Role page-type compiler.
Extracts and applies generated data to the hire-rag-developer.html template.
"""
from .shared import (
    apply_hero, apply_comply, apply_what_is,
    apply_table_section, apply_services,
    apply_process, apply_pricing, apply_faq,
    set_text, set_href,
)


def _apply_stack(soup, third_data):
    """Update the stack/tooling tabs and chipcards."""
    stack_sec = soup.find(id="stack") or soup.find("section", class_=lambda c: c and "stack" in c)
    if not (stack_sec and "stack" in third_data):
        return

    st_data = third_data["stack"]
    sh = st_data.get("sec-head", {})
    set_text(stack_sec.find("h2"), sh.get("h2"))
    set_text(stack_sec.find(class_="eyebrow"), sh.get("eyebrow"))

    # Update tab buttons
    tabs_box = stack_sec.find(class_="stack-tabs")
    if tabs_box and "stack-tabs" in st_data:
        btn_els = tabs_box.find_all("button")
        for i, t_info in enumerate(st_data["stack-tabs"]):
            if i < len(btn_els):
                k_el = btn_els[i].find(class_="k")
                btn_els[i].clear()
                if k_el or "key" in t_info:
                    new_k = k_el or soup.new_tag("span", attrs={"class": "k"})
                    new_k.string = str(t_info.get("key", f"0{i+1}"))
                    btn_els[i].append(new_k)
                    btn_els[i].append(" ")
                btn_els[i].append(str(t_info.get("name", "")))
                if "id" in t_info:
                    btn_els[i]["data-s"] = str(t_info["id"])

    # Update panels chipcard text
    if "stack-panels" in st_data:
        for pid, tools in st_data["stack-panels"].items():
            panel = stack_sec.find(class_="stack-panel", attrs={"data-p": pid})
            if panel and isinstance(tools, list):
                chips = panel.find_all(class_="chipcard")
                for j, tool_name in enumerate(tools):
                    if j < len(chips):
                        # Preserve logo-wrap if present, update text
                        text_span = chips[j].find("span", class_=lambda c: not c or "logo-wrap" not in c)
                        if text_span and text_span != chips[j].find(class_="logo-wrap"):
                            set_text(text_span, tool_name)
                        else:
                            logo_wrap = chips[j].find(class_="logo-wrap")
                            chips[j].clear()
                            if logo_wrap:
                                chips[j].append(logo_wrap)
                                chips[j].append(" ")
                            new_text_span = soup.new_tag("span")
                            new_text_span.string = str(tool_name)
                            chips[j].append(new_text_span)


def _apply_final_cta(soup, final_data):
    """Update the final contact / lets-talk section."""
    final_sec = soup.find(id="lets-talk") or soup.find("section", class_=lambda c: c and "final" in c)
    if not (final_sec and "final" in final_data):
        return

    f_data = final_data["final"]
    set_text(final_sec.find("h2"), f_data.get("h2"))
    set_text(final_sec.find(class_="eyebrow"), f_data.get("eyebrow"))
    set_text(final_sec.find(class_="lede"), f_data.get("lede"))

    fcard = final_sec.find(class_="fcard")
    if fcard and "fcard" in f_data:
        fc_d = f_data["fcard"]
        set_text(fcard.find("h3"), fc_d.get("h3"))
        set_text(fcard.find(class_="sub"), fc_d.get("sub"))
        btn = fcard.find(class_="btn-primary")
        if btn and "btn-primary" in fc_d:
            set_text(btn, fc_d["btn-primary"])


def apply(soup, hero_data, second_data, third_data, final_data):
    """
    Apply all 4 generated JSON payloads to the Hire-a-Role HTML template.
    """
    # ── 1. Hero ──────────────────────────────────────────────────
    if hero_data:
        apply_hero(soup, hero_data)

    # ── 2. Second hero ───────────────────────────────────────────
    if second_data:
        apply_comply(soup, second_data)
        apply_what_is(soup, second_data)

        if "roles" in second_data:
            roles_sec = soup.find(id="roles") or soup.find("section", class_=lambda c: c and "roles" in c)
            apply_table_section(soup, roles_sec, second_data["roles"])
        print("  [OK] Second hero section applied.")

    # ── 3. Third section ─────────────────────────────────────────
    if third_data:
        apply_services(soup, third_data)
        _apply_stack(soup, third_data)
        print("  [OK] Third section applied.")

    # ── 4. Final section ─────────────────────────────────────────
    if final_data:
        if "engagement" in final_data:
            eng_sec = soup.find(id="engagement") or soup.find("section", class_=lambda c: c and "engagement" in c)
            apply_table_section(soup, eng_sec, final_data["engagement"])

        apply_process(soup, final_data)
        apply_pricing(soup, final_data)
        apply_faq(soup, final_data)
        _apply_final_cta(soup, final_data)
        print("  [OK] Final section applied.")

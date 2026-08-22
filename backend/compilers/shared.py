"""
Shared DOM helper utilities used by all page-type compilers.
"""
from bs4 import BeautifulSoup


def set_text(el, text):
    """Set the direct text content of a BeautifulSoup element."""
    if el and text is not None:
        el.string = str(text)


def set_href(el, url):
    """Set the href attribute of a BeautifulSoup element."""
    if el and url:
        el["href"] = str(url)


def apply_hero(soup, hero_data):
    """
    Shared hero section updater — identical across all page types.
    Handles: eyebrow, h1+span, hero-sub, creds, hero-cta, live, trust metrics.
    """
    hero_sec = soup.find("section", class_="hero")
    if not (hero_sec and "hero" in hero_data):
        return

    hd = hero_data["hero"]

    # eyebrow
    set_text(hero_sec.find(class_="eyebrow"), hd.get("eyebrow"))

    # h1
    h1_el = hero_sec.find("h1")
    if h1_el and "h1" in hd:
        h1_data = hd["h1"]
        h1_el.clear()
        if isinstance(h1_data, dict):
            prefix = h1_data.get("h1") or h1_data.get("h1-text") or ""
            if prefix:
                h1_el.append(str(prefix) + " ")
            if "span" in h1_data:
                span_tag = soup.new_tag("span")
                span_tag.string = str(h1_data["span"])
                h1_el.append(span_tag)
            if "suffix" in h1_data:
                h1_el.append(" " + str(h1_data["suffix"]))
        else:
            h1_el.string = str(h1_data)

    # hero-sub
    set_text(hero_sec.find(class_="hero-sub"), hd.get("hero-sub"))

    # creds
    creds_box = hero_sec.find(class_="creds")
    if creds_box and "creds" in hd:
        cred_els = creds_box.find_all(class_="cred")
        for i, c_item in enumerate(hd["creds"]):
            if i < len(cred_els):
                c_dict = c_item.get("cred", c_item)
                t_box = cred_els[i].find(class_="t")
                if t_box:
                    set_text(t_box.find("i"), c_dict.get("i"))
                    set_text(t_box.find("b"), c_dict.get("b"))

    # hero-cta
    cta_box = hero_sec.find(class_="hero-cta")
    if cta_box and "hero-cta" in hd:
        btn_primary = cta_box.find(class_="btn-primary")
        btn_ghost   = cta_box.find(class_="btn-ghost")
        for btn_entry in hd["hero-cta"]:
            if "btn-primary" in btn_entry and btn_primary:
                bp_data = btn_entry["btn-primary"]
                svg = btn_primary.find("svg")
                btn_primary.clear()
                btn_primary.append(str(bp_data.get("text", "")))
                if svg:
                    btn_primary.append(" ")
                    btn_primary.append(svg)
                set_href(btn_primary, bp_data.get("url", "#lets-talk"))
            elif "btn-ghost" in btn_entry and btn_ghost:
                bg_data = btn_entry["btn-ghost"]
                set_text(btn_ghost, bg_data.get("text", ""))
                set_href(btn_ghost, bg_data.get("url", "/ai-case-studies"))

    # live note
    live_el = hero_sec.find(class_="live")
    if live_el and "live" in hd:
        pulse = live_el.find(class_="pulse")
        live_el.clear()
        if pulse:
            live_el.append(pulse)
            live_el.append(" ")
        live_el.append(str(hd["live"]))

    # trust metrics
    trust_box = hero_sec.find(class_="trust")
    if trust_box and "trust" in hd:
        trust_divs = trust_box.find_all("div", recursive=False)
        for i, t_data in enumerate(hd["trust"]):
            if i < len(trust_divs):
                set_text(trust_divs[i].find("b"), t_data.get("b"))
                set_text(trust_divs[i].find("span"), t_data.get("span"))

    print("  [OK] Hero section applied.")


def apply_comply(soup, second_data):
    """Shared comply strip updater."""
    comply_sec = soup.find(class_="comply")
    if comply_sec and "comply" in second_data:
        c_data = second_data["comply"]
        comply_in = comply_sec.find(class_="comply-in")
        if comply_in:
            item_divs = comply_in.find_all("div", recursive=False)
            c_items = c_data.get("comply-in", [])
            for i, c_entry in enumerate(c_items):
                if i < len(item_divs):
                    span_el = item_divs[i].find("span")
                    if span_el:
                        span_el.clear()
                        b_tag = soup.new_tag("b")
                        b_tag.string = str(c_entry.get("b", ""))
                        span_el.append(b_tag)
                        span_el.append(str(c_entry.get("span", "")))


def apply_what_is(soup, second_data):
    """Shared what-is section updater."""
    what_sec = (
        soup.find(id="what-is")
        or soup.find(id=lambda i: i and "what-is" in i)
        or soup.find("section", class_=lambda c: c and "what-is" in c)
    )
    if what_sec and "what-is" in second_data:
        wi_data = second_data["what-is"]
        sh = wi_data.get("sec-head", {})
        set_text(what_sec.find("h2"), sh.get("h2"))
        set_text(what_sec.find(class_="eyebrow"), sh.get("eyebrow"))

        tldr_box = what_sec.find(class_="tldr")
        if tldr_box and "tldr" in wi_data:
            set_text(tldr_box.find("b"), wi_data["tldr"].get("b"))
            p_data = wi_data["tldr"].get("p", [])
            if isinstance(p_data, str):
                p_data = [p_data]
            p_els = tldr_box.find_all("p")
            for i, p_txt in enumerate(p_data):
                if i < len(p_els):
                    set_text(p_els[i], p_txt)
                else:
                    new_p = soup.new_tag("p")
                    new_p.string = str(p_txt)
                    tldr_box.append(new_p)
            for i in range(len(p_data), len(p_els)):
                p_els[i].decompose()


def apply_table_section(soup, sec_el, data):
    """
    Generic table updater for sections that contain a .tablewrap.
    Covers: sec-head (eyebrow, h2), tablewrap (thead + tbody), optional callout or p.
    """
    if not (sec_el and data):
        return
    sh = data.get("sec-head", {})
    set_text(sec_el.find(class_="eyebrow"), sh.get("eyebrow"))
    set_text(sec_el.find("h2"), sh.get("h2"))

    tbl_wrap = sec_el.find(class_="tablewrap")
    if tbl_wrap and "tablewrap" in data:
        tw = data["tablewrap"]
        th_els = tbl_wrap.select("thead th")
        for i, th_txt in enumerate(tw.get("thead", [])):
            if i < len(th_els):
                set_text(th_els[i], th_txt)
        tr_els = tbl_wrap.select("tbody tr")
        for i, row in enumerate(tw.get("tbody", [])):
            if i < len(tr_els):
                set_text(tr_els[i].find("th"), row.get("th"))
                tds = tr_els[i].find_all("td")
                for j, val in enumerate(row.get("td", [])):
                    if j < len(tds):
                        set_text(tds[j], val)

    callout = sec_el.find(class_="callout")
    if callout and "callout" in data:
        c_p = data["callout"].get("p", [])
        if isinstance(c_p, str):
            c_p = [c_p]
        for i, cp_txt in enumerate(callout.find_all("p")):
            if i < len(c_p):
                set_text(cp_txt, c_p[i])
    elif "p" in data:
        p_el = sec_el.find("p", class_="reveal") or sec_el.find("p")
        if p_el:
            set_text(p_el, data["p"])


def apply_services(soup, third_data):
    """Shared services grid updater."""
    svc_sec = soup.find(id="services") or soup.find("section", class_=lambda c: c and "services" in c)
    if not (svc_sec and "services" in third_data):
        return
    s_data = third_data["services"]
    sh = s_data.get("sec-head", {})
    set_text(svc_sec.find("h2"), sh.get("h2"))
    sh_p = svc_sec.find(class_="sec-head")
    if sh_p and sh_p.find("p"):
        set_text(sh_p.find("p"), sh.get("p"))
    set_text(svc_sec.find(class_="eyebrow"), sh.get("eyebrow"))

    grid = svc_sec.find(class_="grid")
    if grid and "grid g3" in s_data:
        cards = grid.find_all(class_="card")
        for i, card_item in enumerate(s_data["grid g3"]):
            if i < len(cards):
                if "card cta-card" in card_item:
                    cta_d = card_item["card cta-card"]
                    set_text(cards[i].find("h3"), cta_d.get("h3"))
                    set_text(cards[i].find("p"), cta_d.get("p"))
                    btn_el = cards[i].find(class_="btn-primary") or cards[i].find("a")
                    if btn_el and "btn-primary" in cta_d:
                        set_text(btn_el, cta_d["btn-primary"].get("text"))
                        set_href(btn_el, cta_d["btn-primary"].get("url"))
                else:
                    c_d = card_item.get("card", card_item)
                    set_text(cards[i].find(class_="n"), c_d.get("n"))
                    set_text(cards[i].find("h3"), c_d.get("h3"))
                    set_text(cards[i].find("p"), c_d.get("p"))


def apply_card_grid_section(soup, sec_el, data):
    """
    Generic card-grid updater (g2 or g3).
    Handles: sec-head (eyebrow, h2), grid of cards (n, h3, p, ul).
    """
    if not (sec_el and data):
        return
    sh = data.get("sec-head", {})
    set_text(sec_el.find(class_="eyebrow"), sh.get("eyebrow"))
    set_text(sec_el.find("h2"), sh.get("h2"))

    grid_el = sec_el.find(class_="grid")
    items_list = data.get("grid g2") or data.get("grid g3") or []
    if not (grid_el and items_list):
        return

    cards = grid_el.find_all(class_="card")
    for i, w_item in enumerate(items_list):
        if i < len(cards):
            w_dict = w_item.get("card", w_item)
            set_text(cards[i].find(class_="n"), w_dict.get("n"))
            set_text(cards[i].find("h3"), w_dict.get("h3"))
            if "p" in w_dict:
                set_text(cards[i].find("p"), w_dict.get("p"))
            ul_el = cards[i].find("ul")
            if ul_el and "ul" in w_dict:
                li_els = ul_el.find_all("li")
                for j, li_txt in enumerate(w_dict["ul"]):
                    if j < len(li_els):
                        set_text(li_els[j], li_txt)
                    else:
                        new_li = soup.new_tag("li")
                        new_li.string = str(li_txt)
                        ul_el.append(new_li)
                for j in range(len(w_dict["ul"]), len(li_els)):
                    li_els[j].decompose()


def apply_process(soup, final_data):
    """Shared process/steps section updater."""
    proc_sec = soup.find(id="process") or soup.find("section", class_=lambda c: c and "process" in c)
    if not (proc_sec and "process" in final_data):
        return
    pr_data = final_data["process"]
    sh = pr_data.get("sec-head", {})
    set_text(proc_sec.find(class_="eyebrow"), sh.get("eyebrow"))
    set_text(proc_sec.find("h2"), sh.get("h2"))

    steps_box = proc_sec.find(class_="steps")
    if steps_box and "steps" in pr_data:
        step_els = steps_box.find_all("details", class_="step")
        for i, s_item in enumerate(pr_data["steps"]):
            if i < len(step_els):
                s_dict = s_item.get("step", s_item)
                num_el = step_els[i].find(class_="num")
                if num_el:
                    days_el = num_el.find(class_="days")
                    num_el.clear()
                    num_el.append(str(s_dict.get("num", f"PHASE 0{i+1}")))
                    if days_el or "days" in s_dict:
                        new_days = days_el or soup.new_tag("span", attrs={"class": "days"})
                        new_days.string = str(s_dict.get("days", ""))
                        num_el.append(new_days)
                set_text(step_els[i].find("h3"), s_dict.get("h3"))
                set_text(step_els[i].find(class_="body"), s_dict.get("body"))


def apply_pricing(soup, final_data):
    """Shared pricing table updater."""
    price_sec = soup.find(id="pricing") or soup.find("section", class_=lambda c: c and "pricing" in c)
    if not (price_sec and "pricing" in final_data):
        return
    pr_data = final_data["pricing"]
    sh = pr_data.get("sec-head", {})
    set_text(price_sec.find(class_="eyebrow"), sh.get("eyebrow"))
    set_text(price_sec.find("h2"), sh.get("h2"))

    tw_price = price_sec.find(class_="tablewrap")
    if tw_price and "tablewrap" in pr_data:
        tw = pr_data["tablewrap"]
        th_els = tw_price.select("thead th")
        for i, th_txt in enumerate(tw.get("thead", [])):
            if i < len(th_els):
                set_text(th_els[i], th_txt)
        tr_els = tw_price.select("tbody tr")
        for i, row in enumerate(tw.get("tbody", [])):
            if i < len(tr_els):
                tds = tr_els[i].find_all("td")
                for j, val in enumerate(row.get("td", [])):
                    if j < len(tds):
                        set_text(tds[j], val)


def apply_faq(soup, final_data):
    """Shared FAQ section updater."""
    faq_sec = soup.find(id="faq") or soup.find("section", class_=lambda c: c and "faq" in c)
    if not (faq_sec and "faq" in final_data):
        return
    fq_data = final_data["faq"]
    sh = fq_data.get("sec-head", {})
    set_text(faq_sec.find(class_="eyebrow"), sh.get("eyebrow"))
    set_text(faq_sec.find("h2"), sh.get("h2"))

    faq_box = faq_sec.find(class_="faq")
    if faq_box and "faq" in fq_data:
        det_els = faq_box.find_all("details")
        for i, f_item in enumerate(fq_data["faq"]):
            f_dict = f_item.get("faq-item", f_item)
            q_txt = f_dict.get("faq-q", "")
            a_txt = f_dict.get("faq-a", "")
            if i < len(det_els):
                set_text(det_els[i].find("summary"), q_txt)
                set_text(det_els[i].find(class_="a"), a_txt)
            else:
                new_det = soup.new_tag("details")
                new_sum = soup.new_tag("summary")
                new_sum.string = q_txt
                new_a = soup.new_tag("div", attrs={"class": "a"})
                new_a.string = a_txt
                new_det.append(new_sum)
                new_det.append(new_a)
                faq_box.append(new_det)

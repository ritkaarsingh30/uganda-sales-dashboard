import os
from name_map import mr_display_name

MONTH_ORDER = ["jan", "feb", "mar", "apr", "may", "jun",
               "jul", "aug", "sep", "oct", "nov", "dec"]

# These are supervisors, not field MRs — exclude from all AI analysis
SUPERVISOR_NAMES = {"Okodi Daniel", "Sarvesh Mallah"}


def _safe(val, default=0):
    try:
        v = float(val)
        import math
        return default if (math.isnan(v) or math.isinf(v)) else v
    except Exception:
        return default


def build_insights_prompt(data: dict, annual_projections: dict) -> str:
    lines = ["# Uganda Pharma Dashboard — Full Data Summary\n"]

    sorted_months = sorted(data.keys(), key=lambda m: MONTH_ORDER.index(m) if m in MONTH_ORDER else 99)

    # ── Per-month summary ─────────────────────────────────────────────────
    lines.append("## Month-by-Month Performance\n")
    prev_sales = None
    product_totals: dict[str, float] = {}

    for mk in sorted_months:
        mdata   = data[mk]
        label   = mk.upper()
        sales_df = mdata.get("sales", {}).get("current")
        proj_df  = mdata.get("projection", {}).get("projection")
        monthly  = mdata.get("monthly", {}).get("delegates")
        exp      = mdata.get("expense", {})

        total_sales = 0.0
        if sales_df is not None and not sales_df.empty and "TOTAL_VALUE_EUR" in sales_df.columns:
            total_sales = _safe(sales_df["TOTAL_VALUE_EUR"].sum())
            for _, row in sales_df.iterrows():
                prod = str(row.get("Product", "")).strip()
                product_totals[prod] = product_totals.get(prod, 0.0) + _safe(row.get("TOTAL_VALUE_EUR", 0))

        total_proj = 0.0
        if proj_df is not None and not proj_df.empty and "Target_Value_EUR" in proj_df.columns:
            total_proj = _safe(proj_df["Target_Value_EUR"].sum())

        ach = (total_sales / total_proj * 100) if total_proj else 0.0
        mom = ((total_sales - prev_sales) / prev_sales * 100) if prev_sales and prev_sales > 0 else None

        spent_eur   = _safe(exp.get("total_spent_eur", 0))
        balance_eur = _safe(exp.get("balance_eur", 0))
        budget_eur  = _safe(exp.get("total_received_eur", 0))

        # Visits
        visits_df   = mdata.get("visits")
        visit_count = 0
        if visits_df is not None and not visits_df.empty and "Visit_Date" in visits_df.columns:
            visit_count = int(visits_df["Visit_Date"].notna().sum())

        # MR-level totals
        pres = pharm = drs = 0
        if monthly is not None and not monthly.empty:
            pres  = int(_safe(monthly["Prescriber"].sum()))    if "Prescriber"    in monthly.columns else 0
            pharm = int(_safe(monthly["PharmacyCalls"].sum())) if "PharmacyCalls" in monthly.columns else 0
            drs   = int(_safe(monthly["DrsConverted"].sum()))  if "DrsConverted"  in monthly.columns else 0

        mom_str = f", MoM {mom:+.1f}%" if mom is not None else ""
        lines.append(f"### {label}")
        lines.append(f"  Sales: {total_sales:.2f} EUR | Target: {total_proj:.2f} EUR | Achievement: {ach:.1f}%{mom_str}")
        lines.append(f"  Visits: {visit_count} | Prescriber Calls: {pres} | Pharmacy Calls: {pharm} | DRs Converted: {drs}")
        lines.append(f"  Activity Budget: {budget_eur:.2f} EUR | Spent: {spent_eur:.2f} EUR | Balance: {balance_eur:.2f} EUR")

        # Top 3 products this month
        if sales_df is not None and not sales_df.empty and "TOTAL_VALUE_EUR" in sales_df.columns and "Product" in sales_df.columns:
            top = sales_df.nlargest(3, "TOTAL_VALUE_EUR")[["Product", "TOTAL_VALUE_EUR"]]
            prod_str = ", ".join(f"{r['Product']} ({_safe(r['TOTAL_VALUE_EUR']):.2f} EUR)" for _, r in top.iterrows())
            lines.append(f"  Top Products: {prod_str}")

        # Per-MR performance
        if monthly is not None and not monthly.empty and "Delegate" in monthly.columns:
            lines.append("  MR Performance:")
            for _, r in monthly.iterrows():
                raw_name  = str(r.get("Delegate", "")).strip()
                name      = mr_display_name(raw_name)
                if name in SUPERVISOR_NAMES:
                    continue
                calls     = int(_safe(r.get("TotalCalls", 0)))
                orders    = _safe(r.get("TotalOrders", 0))
                ctc       = _safe(r.get("CTC", 0))
                ctc_ratio = (ctc / orders * 100) if orders > 0 else 0.0
                days      = int(_safe(r.get("DaysWorked", 0)))
                dr_conv   = int(_safe(r.get("DrsConverted", 0)))
                lines.append(
                    f"    {name}: {calls} calls, {orders:.2f} EUR orders, "
                    f"CTC {ctc:.2f} EUR ({ctc_ratio:.1f}%), {days} days worked, {dr_conv} DRs converted"
                )

        lines.append("")
        prev_sales = total_sales

    # ── Overall product leaderboard ───────────────────────────────────────
    if product_totals:
        lines.append("## Top 10 Products (all months combined)")
        for prod, val in sorted(product_totals.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  {prod}: {val:.2f} EUR")
        lines.append("")

    # ── Annual projection context ─────────────────────────────────────────
    if annual_projections:
        lines.append(f"## Annual Projections: {len(annual_projections)} products tracked")

    return "\n".join(lines)


def build_delegate_prompt(data: dict) -> str:
    lines = ["# Uganda Pharma — MR Field Force Data\n"]
    sorted_months = sorted(data.keys(), key=lambda m: MONTH_ORDER.index(m) if m in MONTH_ORDER else 99)

    # Aggregate per-MR across all months
    mr_agg: dict[str, dict] = {}
    for mk in sorted_months:
        monthly = data[mk].get("monthly", {}).get("delegates")
        tour_df = data[mk].get("tour")
        if monthly is None or monthly.empty:
            continue
        for _, r in monthly.iterrows():
            raw = str(r.get("Delegate", "")).strip()
            name = mr_display_name(raw)
            if name in SUPERVISOR_NAMES:
                continue
            if name not in mr_agg:
                mr_agg[name] = {"calls": 0, "orders": 0.0, "ctc": 0.0, "days": 0,
                                "drs": 0, "prescriber": 0, "pharmacy": 0,
                                "tour_planned": 0, "tour_covered": 0, "months": []}
            a = mr_agg[name]
            a["calls"]      += int(_safe(r.get("TotalCalls", 0)))
            a["orders"]     += _safe(r.get("TotalOrders", 0))
            a["ctc"]        += _safe(r.get("CTC", 0))
            a["days"]       += int(_safe(r.get("DaysWorked", 0)))
            a["drs"]        += int(_safe(r.get("DrsConverted", 0)))
            a["prescriber"] += int(_safe(r.get("Prescriber", 0)))
            a["pharmacy"]   += int(_safe(r.get("PharmacyCalls", 0)))
            a["months"].append(mk.upper())
            if tour_df is not None and not tour_df.empty and "MR" in tour_df.columns:
                mt = tour_df[tour_df["MR"] == raw]
                a["tour_planned"] += len(mt)
                a["tour_covered"] += int(mt["Covered"].sum()) if "Covered" in mt.columns else 0

    lines.append("## Per-MR Aggregated Performance (all months)\n")
    for name, a in sorted(mr_agg.items(), key=lambda x: -x[1]["orders"]):
        ctc_ratio = (a["ctc"] / a["orders"] * 100) if a["orders"] > 0 else None
        conv_rate = (a["drs"] / a["calls"] * 100) if a["calls"] > 0 else 0.0
        tour_pct  = (a["tour_covered"] / a["tour_planned"] * 100) if a["tour_planned"] > 0 else None
        ctc_str   = f"CTC {a['ctc']:.2f} EUR ({ctc_ratio:.1f}%)" if ctc_ratio is not None else f"CTC {a['ctc']:.2f} EUR (no orders)"
        tour_str  = f"Tour {a['tour_covered']}/{a['tour_planned']} ({tour_pct:.0f}%)" if tour_pct is not None else "No tour data"
        lines.append(
            f"  {name}: {a['calls']} calls, {a['orders']:.2f} EUR orders, {ctc_str}, "
            f"{a['days']} days, {a['drs']} DRs converted ({conv_rate:.1f}% conv rate), "
            f"{a['prescriber']} prescriber / {a['pharmacy']} pharmacy calls, {tour_str}, "
            f"active in: {', '.join(a['months'])}"
        )

    lines.append("\n## Team Totals")
    total_orders = sum(a["orders"] for a in mr_agg.values())
    total_ctc    = sum(a["ctc"] for a in mr_agg.values())
    total_calls  = sum(a["calls"] for a in mr_agg.values())
    lines.append(f"  Total orders: {total_orders:.2f} EUR | Total CTC: {total_ctc:.2f} EUR | "
                 f"Team CTC ratio: {(total_ctc/total_orders*100):.1f}% | Total calls: {total_calls}")
    return "\n".join(lines)


def build_activity_prompt(data: dict) -> str:
    lines = ["# Uganda Pharma — Activity & Expense Data\n"]
    sorted_months = sorted(data.keys(), key=lambda m: MONTH_ORDER.index(m) if m in MONTH_ORDER else 99)

    total_planned = total_exec = total_not_exec = total_unplanned = 0
    total_with_outcome = total_without_outcome = 0
    total_planned_ugx = total_spent_ugx = total_spent_eur = 0.0
    activity_type_stats: dict[str, dict] = {}
    mr_exec: dict[str, dict] = {}

    for mk in sorted_months:
        ae_df = data[mk].get("expense", {}).get("activity_exp")
        if ae_df is None or ae_df.empty:
            continue
        label = mk.upper()
        lines.append(f"## {label} Activities")
        for _, r in ae_df.iterrows():
            act    = str(r.get("Activity", "VISIT")).strip()
            resp   = mr_display_name(str(r.get("Responsible", r.get("Delegate", "Unknown"))).strip())
            if resp in SUPERVISOR_NAMES:
                continue
            amt    = _safe(r.get("Amount_EUR", 0))
            visits = int(_safe(r.get("Num_Visits", r.get("num_visits", 0))))
            outcome = str(r.get("Sales_Outcome", r.get("sales_outcome", ""))).strip()
            has_out = bool(outcome and outcome not in ("", "0", "nan", "None"))

            total_spent_eur   += amt
            total_with_outcome    += 1 if has_out else 0
            total_without_outcome += 0 if has_out else 1

            if act not in activity_type_stats:
                activity_type_stats[act] = {"count": 0, "with_outcome": 0, "spent_eur": 0.0}
            activity_type_stats[act]["count"]        += 1
            activity_type_stats[act]["with_outcome"] += 1 if has_out else 0
            activity_type_stats[act]["spent_eur"]    += amt

            if resp not in mr_exec:
                mr_exec[resp] = {"planned": 0, "executed": 0}
            mr_exec[resp]["planned"]  += 1
            mr_exec[resp]["executed"] += 1  # activity_exp entries are executed

        lines.append(f"  {len(ae_df)} activities logged, {ae_df['Amount_EUR'].sum():.2f} EUR spent")

    lines.append("\n## Activity Type Breakdown (all months)")
    for act, s in sorted(activity_type_stats.items(), key=lambda x: -x[1]["spent_eur"]):
        out_rate = (s["with_outcome"] / s["count"] * 100) if s["count"] else 0
        lines.append(f"  {act}: {s['count']} activities, {s['spent_eur']:.2f} EUR, "
                     f"{s['with_outcome']} with sales outcome ({out_rate:.0f}% outcome rate)")

    cost_per_out = (total_spent_eur / total_with_outcome) if total_with_outcome else None
    lines.append(f"\n## Overall: {total_with_outcome} with outcome / {total_without_outcome} without outcome | "
                 f"Total spent: {total_spent_eur:.2f} EUR"
                 + (f" | Cost per outcome: {cost_per_out:.2f} EUR" if cost_per_out else ""))
    return "\n".join(lines)


async def generate_delegate_insights(data: dict) -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return "AI insights unavailable — set GROQ_API_KEY in .env"
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        prompt = build_delegate_prompt(data)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": (
                    "You are a senior pharma sales manager reviewing Uganda field force performance.\n\n"
                    "IMPORTANT: Okodi Daniel and Sarvesh Mallah are supervisors, not field MRs. "
                    "Ignore any data attributed to them and do not mention them in your insights.\n\n"
                    "Produce exactly 4 insights. Each must:\n"
                    "- Cite specific MR names, EUR amounts, call counts, conversion rates, and CTC ratios from the data.\n"
                    "- Explain the business implication (why this matters).\n"
                    "- End with a concrete coaching or managerial action.\n"
                    "- Be 3-5 sentences long.\n\n"
                    "Cover one angle each:\n"
                    "1. Top MR performer — who leads in orders, what drives their success (calls, conversion, days).\n"
                    "2. Underperforming MR(s) — if any MR has zero or very low orders, name them and recommend intervention. "
                    "   If ALL MRs have meaningful orders, emit a GOOD insight celebrating this instead — do NOT invent a hypothetical warning.\n"
                    "3. CTC efficiency — if any MR has CTC ratio > 20%, flag them with specifics; if all ratios are healthy, say so as GOOD.\n"
                    "4. Tour plan adherence — who has the best/worst coverage %, link to their sales outcome.\n\n"
                    "CRITICAL: Never generate hypothetical or 'if X were the case' statements. Every sentence must reference actual names and numbers from the data provided. If there is nothing negative to report for an angle, write a GOOD insight instead.\n\n"
                    "Output format — exactly 4 lines, nothing else:\n"
                    "[TYPE] TITLE | Paragraph.\n"
                    "TYPE = GOOD | WARN | DANGER | INFO — TITLE = 3-5 words ALL CAPS. No numbering, no extra lines."
                )},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Insights generation failed: {e}"


async def generate_activity_insights(data: dict) -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return "AI insights unavailable — set GROQ_API_KEY in .env"
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        prompt = build_activity_prompt(data)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": (
                    "You are a senior pharma sales analyst reviewing Uganda field activity data.\n\n"
                    "IMPORTANT: Okodi Daniel and Sarvesh Mallah are supervisors, not field MRs. "
                    "Ignore any data attributed to them and do not mention them in your insights.\n\n"
                    "Produce exactly 4 insights. Each must:\n"
                    "- Cite specific activity types, EUR amounts, outcome rates, and MR names from the data.\n"
                    "- Explain the ROI or efficiency implication.\n"
                    "- End with a concrete recommended action to improve activity effectiveness.\n"
                    "- Be 3-5 sentences long.\n\n"
                    "Cover one angle each:\n"
                    "1. Best-ROI activity type — which activity type generates the most sales outcomes per EUR spent.\n"
                    "2. Wasteful activity spend — activity types with high spend but low outcome rate; if all types are efficient, emit GOOD.\n"
                    "3. Cost per outcome — overall cost per sales-outcome, and which activities drive it up or down.\n"
                    "4. Activity volume vs outcomes — total activities logged vs those with sales outcomes, and what that conversion rate means.\n\n"
                    "CRITICAL: Never write hypothetical or 'if X were the case' statements. Every sentence must cite actual activity types, amounts, and rates from the data. If no negative pattern exists, write a GOOD insight instead.\n\n"
                    "Output format — exactly 4 lines, nothing else:\n"
                    "[TYPE] TITLE | Paragraph.\n"
                    "TYPE = GOOD | WARN | DANGER | INFO — TITLE = 3-5 words ALL CAPS. No numbering, no extra lines."
                )},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Insights generation failed: {e}"


async def generate_insights(data: dict, annual_projections: dict) -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return "AI insights unavailable — set GROQ_API_KEY in .env"
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        prompt = build_insights_prompt(data, annual_projections)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": (
                    "You are a senior pharma sales analyst writing a management briefing for Uganda field sales.\n\n"
                    "IMPORTANT: Okodi Daniel and Sarvesh Mallah are supervisors, not field MRs. "
                    "Ignore any data attributed to them and do not mention them in your insights.\n\n"
                    "Produce exactly 6 insights. Each insight must:\n"
                    "- Be grounded entirely in the numbers provided — no generic statements.\n"
                    "- Name specific MRs, products, and EUR amounts.\n"
                    "- Explain the WHY and the business impact, not just the fact.\n"
                    "- End with a concrete recommended action (what the manager should do next).\n"
                    "- Be 4-6 sentences long.\n\n"
                    "Cover these angles across the 6 insights (one each):\n"
                    "1. Month-over-month sales trend — what drove growth or decline, which MRs/products shifted.\n"
                    "2. Target achievement — which months hit/missed, gap in EUR, what that means for annual target.\n"
                    "3. CTC ratio analysis — flag any MR where CTC/orders ratio is high or orders are zero; if all healthy, emit GOOD.\n"
                    "4. Field activity vs budget — over/underspend, link to visit counts and DRs converted.\n"
                    "5. Product performance — top performers, any products with zero or declining sales across months.\n"
                    "6. MR individual spotlight — best and worst MR by orders, with specific calls/days/conversion data.\n\n"
                    "CRITICAL: Never write hypothetical or 'if X were the case' statements. Every sentence must cite actual names and numbers from the data. If nothing negative exists for an angle, write a GOOD insight celebrating the positive.\n\n"
                    "Output format — exactly 6 lines, nothing else:\n"
                    "[TYPE] TITLE | Paragraph here.\n\n"
                    "TYPE = GOOD | WARN | DANGER | INFO\n"
                    "TITLE = 3-5 words ALL CAPS\n"
                    "No numbering, no bullets, no blank lines, no extra text."
                )},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Insights generation failed: {e}"

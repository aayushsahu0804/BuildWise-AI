"""BuildWise AI — construction intelligence in a single Streamlit application."""
from __future__ import annotations

import json
import hashlib
import os
import re
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

import streamlit as st

APP_NAME = "BuildWise AI"
MODEL_DEFAULT = "gemini-3.8-flash"
STRUCTURE_RATES = {"Residential house": 2_200, "Apartment building": 2_650, "Commercial building": 3_000, "Warehouse / industrial": 1_850, "Renovation": 1_500}
TIER_MULTIPLIERS = {"Value": 0.85, "Standard": 1.0, "Premium": 1.35, "Luxury": 1.8}
CITY_MULTIPLIERS = {"Bengaluru": 1.08, "Chennai": 1.02, "Delhi NCR": 1.12, "Hyderabad": 1.0, "Kolkata": 0.92, "Mumbai": 1.22, "Pune": 1.05, "Other / national average": 1.0}

st.set_page_config(page_title=APP_NAME, page_icon="🏗️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root { --ink:#18251f; --muted:#66746c; --green:#1c7153; --lime:#c7ef74; --paper:#f5f7f2; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background:var(--paper); color:var(--ink); }
[data-testid="stSidebar"] { background:#18251f; }
[data-testid="stSidebar"] * { color:#eef4ed !important; }
h1,h2,h3 { font-family:'Manrope',sans-serif !important; letter-spacing:-.035em; }
.hero { padding:2rem 2.2rem; border-radius:22px; background:linear-gradient(120deg,#163f32,#1d7152); color:#fff; margin:.4rem 0 1.4rem; }
.hero h1 { color:#fff; margin:0; font-size:2.45rem; }
.hero p { color:#d9e9dd; margin:.45rem 0 0; max-width:800px; }
.eyebrow { color:var(--lime); text-transform:uppercase; letter-spacing:.13em; font-size:.72rem; font-weight:700; }
.metric-card { background:#fff; border:1px solid #e4e9e1; border-radius:15px; padding:1.05rem 1.1rem; min-height:105px; box-shadow:0 4px 18px #21392c0a; }
.metric-label { color:var(--muted); font-size:.77rem; text-transform:uppercase; letter-spacing:.06em; font-weight:700; }
.metric-value { color:var(--ink); font-family:'Manrope',sans-serif; font-size:1.55rem; font-weight:800; padding-top:.32rem; }
.section-note { color:var(--muted); margin-top:-.55rem; margin-bottom:1.2rem; }
.tag { display:inline-block; background:#e6f2e9; color:#1c6249; border-radius:999px; padding:.28rem .65rem; font-size:.78rem; font-weight:700; }
.demo-note { border-left:4px solid #d39b34; background:#fff6df; padding:.75rem 1rem; border-radius:8px; color:#5a4826; margin:.65rem 0 1rem; }
.disclaimer { background:#fff5df; border:1px solid #f0d89d; border-radius:12px; padding:.85rem 1rem; color:#624c1e; }
div.stButton > button[kind="primary"] { background:#1c7153; border-color:#1c7153; border-radius:10px; font-weight:700; }
div.stButton > button[kind="primary"]:hover { background:#15543e; border-color:#15543e; }
</style>
""", unsafe_allow_html=True)


def get_secret(name: str) -> str | None:
    """Read secrets server-side, supporting Streamlit secrets and environment variables."""
    try:
        value = st.secrets.get(name)
        if value is not None:
            value = str(value).strip()
            if value:
                return value
    except Exception:
        pass
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def money(value: float) -> str:
    value = max(0, float(value))
    if value >= 10_000_000:
        return f"₹{value / 10_000_000:.2f} Cr"
    if value >= 100_000:
        return f"₹{value / 100_000:.2f} L"
    return f"₹{value:,.0f}"


def estimate_project(structure: str, area: float, city: str, tier: str, completion: float) -> dict[str, Any]:
    if area <= 0 or area > 10_000_000:
        raise ValueError("Area must be greater than 0 and no more than 10,000,000 sq ft.")
    if not 0 <= completion <= 100:
        raise ValueError("Completion percentage must be between 0 and 100.")
    rate = STRUCTURE_RATES[structure]
    city_factor = CITY_MULTIPLIERS[city]
    tier_factor = TIER_MULTIPLIERS[tier]
    budget = area * rate * city_factor * tier_factor
    progress = completion / 100
    # Planning-level quantity allowances per square foot; not a bill of quantities.
    materials = {
        "Cement": {"quantity": round(area * 0.40, 1), "unit": "bags (50 kg)"},
        "Steel": {"quantity": round(area * 3.5, 1), "unit": "kg"},
        "Sand": {"quantity": round(area * 1.8, 1), "unit": "cu ft"},
        "Aggregate": {"quantity": round(area * 1.3, 1), "unit": "cu ft"},
        "Bricks / blocks": {"quantity": round(area * 8, 0), "unit": "units"},
    }
    # Indicative finished-property value per built sq ft, city + tier adjusted.
    base_value_rate = 4_500 * city_factor * tier_factor
    valuation = area * base_value_rate
    return {
        "structure_type": structure, "area_sq_ft": area, "city": city, "property_tier": tier,
        "completion_percent": completion, "estimated_total_budget_inr": round(budget),
        "incurred_cost_inr": round(budget * progress), "remaining_budget_inr": round(budget * (1-progress)),
        "project_progress_percent": completion, "material_estimates": materials,
        "indicative_property_valuation_inr": round(valuation),
        "assumptions": {
            "base_construction_rate_inr_per_sq_ft": rate, "city_multiplier": city_factor,
            "property_tier_multiplier": tier_factor,
            "budget_formula": "area × structure base rate × city multiplier × tier multiplier",
            "valuation_formula": "area × ₹4,500/sq ft × city multiplier × tier multiplier",
            "materials_note": "Indicative early-stage allowances only; actual quantities depend on drawings, specification, soil and local codes.",
            "valuation_note": "Indicative estimate only; excludes land-title, market comparables, taxes and professional valuation.",
        },
    }


def demo_safety(filename: str) -> dict[str, Any]:
    return {
        "analysis_mode": "Demo mode",
        "safety_score": 72,
        "summary": f"Demo assessment for {filename}: a mixed-readiness scene with several controls to verify.",
        "ppe_checklist": [
            {"item": "Hard hats", "status": "Needs verification", "observation": "Confirm all workers in active zones wear fitted hard hats."},
            {"item": "High-visibility vests", "status": "Needs verification", "observation": "Check visibility garments, especially around vehicle routes."},
            {"item": "Safety footwear", "status": "Not assessable", "observation": "Foot protection cannot be reliably confirmed from this view."},
            {"item": "Eye / hand protection", "status": "Not assessable", "observation": "Verify task-specific PPE at workstations."},
        ],
        "hazards": [
            {"hazard": "Unprotected edge or opening", "severity": "High", "location": "Elevated work area", "corrective_action": "Stop access and install compliant guardrails or secured covers; inspect before restart."},
            {"hazard": "Housekeeping / trip exposure", "severity": "Medium", "location": "Access route", "corrective_action": "Clear debris, route cables safely and keep walkways unobstructed."},
            {"hazard": "PPE compliance uncertain", "severity": "Medium", "location": "Work zone", "corrective_action": "Supervisor to verify and record required PPE before work continues."},
        ],
        "corrective_actions": ["Secure elevated edges and openings before access.", "Restore clear, marked pedestrian access routes.", "Have a competent site supervisor verify task-specific PPE."],
        "limitations": "DEMO MODE: This is fixed sample content, not an analysis of the uploaded image.",
    }


def demo_crack(filename: str) -> dict[str, Any]:
    return {
        "analysis_mode": "Demo mode",
        "summary": f"Demo assessment for {filename}: sample crack triage for demonstration only.",
        "possible_crack_types": [
            {"type": "Diagonal / shear-like", "likelihood": "Possible", "observation": "Demonstration category; image has not been analyzed."},
            {"type": "Shrinkage / hairline", "likelihood": "Possible", "observation": "Demonstration category; confirm width and pattern on site."},
        ],
        "severity": "Moderate (demo estimate)", "probable_causes": ["Differential movement", "Drying shrinkage", "Thermal movement"],
        "recommended_repairs": ["Photograph and map the crack with a scale; record width and date.", "Monitor for change and check both sides where accessible.", "Ask a licensed structural engineer to assess before selecting a repair."],
        "urgency": "Arrange a qualified inspection soon; restrict the area if movement, falling material or instability is suspected.",
        "limitations": "DEMO MODE: This is fixed sample content, not an analysis of the uploaded image.",
    }


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text.strip(), flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("The AI returned an unreadable report. Please try again.")
    value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("The AI response was not a JSON object.")
    return value


def analyze_image(image_bytes: bytes, mime: str, mode: str, filename: str) -> dict[str, Any]:
    api_key = get_secret("GEMINI_API_KEY")
    if not api_key:
        return demo_safety(filename) if mode == "safety" else demo_crack(filename)
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        if mode == "safety":
            prompt = """Inspect this construction site image for a preliminary visual safety audit. Do not assert details that are not visible; say not assessable where needed. Return ONLY valid JSON with keys: safety_score (integer 0-100), summary (string), ppe_checklist (array of objects item/status/observation), hazards (array of objects hazard/severity [Critical/High/Medium/Low]/location/corrective_action), corrective_actions (array of strings), limitations (string). Prioritize immediate life-safety risks. This is not a substitute for an on-site competent-person inspection."""
        else:
            prompt = """Inspect this image for visible cracking and provide preliminary triage only. Do not diagnose structural safety from a photo; distinguish observations from possibilities and say when the image is insufficient. Return ONLY valid JSON with keys: summary (string), possible_crack_types (array of objects type/likelihood/observation), severity (string), probable_causes (array of strings), recommended_repairs (array of strings), urgency (string), limitations (string). Include conservative escalation advice."""
        model = get_secret("GEMINI_MODEL") or MODEL_DEFAULT
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=[prompt, image],
            # Gemini 3 models use their default sampling settings; JSON mode keeps
            # the report machine-readable without relying on unsupported tuning.
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        result = _extract_json(response.text or "")
        result["analysis_mode"] = "Gemini AI"
        result["analysis_model"] = model
        return result
    except Exception:
        # Keep provider exceptions out of the UI and logs. Never echo request details.
        # The deterministic fallback makes clear that the uploaded image was not analyzed.
        report = demo_safety(filename) if mode == "safety" else demo_crack(filename)
        report["analysis_mode"] = "Demo fallback"
        report["fallback_notice"] = (
            "Gemini could not complete this request. This fixed demo report is not based on the uploaded image. "
            "Check the server-side API configuration and try again."
        )
        report["limitations"] += " Gemini did not analyze the uploaded image; this is a deterministic sample."
        return report


def metric(label: str, value: str) -> None:
    st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>', unsafe_allow_html=True)


def show_json_download(label: str, data: dict[str, Any], filename: str) -> None:
    st.download_button(label, json.dumps(data, indent=2, ensure_ascii=False), file_name=filename, mime="application/json", use_container_width=True)


def section_header(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="eyebrow" style="color:#1c7153">{kicker}</div><h1 style="margin:.1rem 0 .8rem">{title}</h1><div class="section-note">{subtitle}</div>', unsafe_allow_html=True)


st.sidebar.markdown("## 🏗️ BuildWise AI")
st.sidebar.caption("Construction intelligence platform")
page = st.sidebar.radio("Navigate", ["Overview", "Site Safety Audit", "Crack Analysis", "Planning & Valuation", "Construction Assistant"], label_visibility="collapsed")
api_available = bool(get_secret("GEMINI_API_KEY"))
st.sidebar.markdown("---")
st.sidebar.markdown("**Gemini configuration**")
if api_available:
    st.sidebar.markdown("🟡 API key configured · request unverified")
    st.sidebar.caption("The image modules confirm Gemini availability per request. Failed requests are labelled as demo fallback.")
else:
    st.sidebar.markdown("🟠 Demo mode · no API key configured")
    st.sidebar.caption("Image uploads are not analyzed; the app returns fixed demo examples.")
st.sidebar.markdown("---")
st.sidebar.caption("Planning aid only. Verify decisions with qualified local professionals.")

if page == "Overview":
    st.markdown('<div class="hero"><div class="eyebrow">Field-ready intelligence</div><h1>Build with better visibility.</h1><p>One workspace for site safety, crack triage, project estimates, and practical construction guidance.</p></div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1: metric("Intelligence modules", "04")
    with c2: metric("Estimate currency", "INR ₹")
    with c3: metric("Current analysis mode", "Gemini AI" if api_available else "Demo")
    st.markdown("### Explore the platform")
    cards = st.columns(2)
    modules = [("01 · Site Safety & PPE", "Review visible PPE, hazards, severity and corrective actions."), ("02 · Structural Crack Analysis", "Triage visible cracks, possible causes and urgency."), ("03 · Planning & Valuation", "Estimate budget, progress, material allowances and indicative value."), ("04 · Construction Assistant", "Get actionable guidance adjusted for weather conditions.")]
    for col, (title, desc) in zip(cards * 2, modules):
        with col:
            st.markdown(f"**{title}**  \n{desc}")
    if not api_available:
        st.markdown('<div class="demo-note"><b>Demo mode is active.</b> Image uploads show fixed examples and are not analyzed. Configure GEMINI_API_KEY to enable Gemini image analysis.</div>', unsafe_allow_html=True)

elif page in ("Site Safety Audit", "Crack Analysis"):
    is_safety = page == "Site Safety Audit"
    section_header("Visual assessment", "Site Safety & PPE Audit" if is_safety else "Structural Crack Analysis", "Upload a clear construction-site image. Keep identifying or sensitive information out of uploads.")
    if not api_available:
        st.markdown('<div class="demo-note"><b>DEMO MODE.</b> Results are deterministic sample outputs and are not based on the uploaded image.</div>', unsafe_allow_html=True)
    if not is_safety:
        st.markdown('<div class="disclaimer"><b>Preliminary visual triage only.</b> AI results do not replace a professional inspection. If a crack is widening, accompanied by displacement, falling material, or suspected instability, keep people clear and contact a licensed structural engineer promptly.</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Choose a JPG or PNG image", type=["jpg", "jpeg", "png"], accept_multiple_files=False, key="safety_upload" if is_safety else "crack_upload")
    if uploaded:
        if uploaded.size > 15 * 1024 * 1024:
            st.error("Image is larger than 15 MB. Please upload a smaller image.")
        else:
            left, right = st.columns([1,1])
            with left: st.image(uploaded, caption=uploaded.name, use_container_width=True)
            with right:
                if st.button("Run safety audit" if is_safety else "Analyze crack image", type="primary", use_container_width=True):
                    try:
                        with st.spinner("Preparing the report…" if not api_available else "Analyzing image with Gemini…"):
                            report = analyze_image(uploaded.getvalue(), uploaded.type, "safety" if is_safety else "crack", uploaded.name)
                        report["report_type"] = "site_safety_audit" if is_safety else "structural_crack_analysis"
                        report["filename"] = uploaded.name
                        report["image_sha256"] = hashlib.sha256(uploaded.getvalue()).hexdigest()
                        report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
                        st.session_state["last_image_report"] = report
                    except RuntimeError as exc:
                        st.error(str(exc))
            report = st.session_state.get("last_image_report")
            if (report and report.get("filename") == uploaded.name
                    and report.get("image_sha256") == hashlib.sha256(uploaded.getvalue()).hexdigest()
                    and report.get("report_type") == ("site_safety_audit" if is_safety else "structural_crack_analysis")):
                st.markdown("---")
                st.markdown("### Assessment report")
                if report.get("analysis_mode") == "Gemini AI":
                    model_used = report.get("analysis_model", MODEL_DEFAULT)
                    st.success(f"Gemini API analyzed this uploaded image · model: {model_used}")
                elif report.get("analysis_mode") == "Demo fallback":
                    st.warning(report.get("fallback_notice", "Gemini analysis failed; this demo output is not based on the uploaded image."))
                else:
                    st.info("DEMO MODE: this fixed example is not based on the uploaded image. No Gemini analysis was completed.")
                if is_safety:
                    score = report.get("safety_score")
                    if isinstance(score, (int,float)):
                        a,b = st.columns([1,3])
                        with a: metric("Safety score", f"{score}/100")
                        with b: st.info(report.get("summary", ""))
                    else: st.write(report.get("summary", ""))
                    st.markdown("#### PPE checklist")
                    for item in report.get("ppe_checklist", []):
                        st.markdown(f"**{item.get('item','Item')}** · {item.get('status','Unknown')}  \n{item.get('observation','')}")
                    st.markdown("#### Hazards & corrective actions")
                    for hazard in report.get("hazards", []):
                        st.markdown(f"**{hazard.get('severity','Unrated')} · {hazard.get('hazard','Hazard')}** — {hazard.get('location','Location not stated')}  \n{hazard.get('corrective_action','')}")
                    if report.get("corrective_actions"):
                        st.markdown("#### Priority actions")
                        for action in report["corrective_actions"]: st.markdown(f"- {action}")
                else:
                    st.markdown(f"**Summary:** {report.get('summary','')}")
                    st.markdown(f"**Severity:** {report.get('severity','Not determined')} · **Urgency:** {report.get('urgency','Not stated')}")
                    st.markdown("#### Possible crack types")
                    for item in report.get("possible_crack_types", []): st.markdown(f"- **{item.get('type','Type')}** ({item.get('likelihood','uncertain')}): {item.get('observation','')}")
                    st.markdown("#### Probable causes to investigate")
                    for cause in report.get("probable_causes", []): st.markdown(f"- {cause}")
                    st.markdown("#### Recommended next steps")
                    for action in report.get("recommended_repairs", []): st.markdown(f"- {action}")
                    st.markdown('<div class="disclaimer">AI results are preliminary and do not replace professional inspection.</div>', unsafe_allow_html=True)
                if report.get("limitations"): st.caption(report["limitations"])
                show_json_download("⬇ Download JSON report", report, "buildwise_safety_report.json" if is_safety else "buildwise_crack_report.json")

elif page == "Planning & Valuation":
    section_header("Project intelligence", "Planning & Real Estate Valuation", "A transparent early-stage estimate in INR. Local rates and quantities should be checked against project documents.")
    with st.form("estimate_form"):
        a,b = st.columns(2)
        with a:
            structure = st.selectbox("Structure type", list(STRUCTURE_RATES.keys()))
            area = st.number_input("Built-up area (sq ft)", min_value=0.0, max_value=10_000_000.0, value=1500.0, step=100.0)
            city = st.selectbox("City", list(CITY_MULTIPLIERS.keys()))
        with b:
            tier = st.selectbox("Property tier", list(TIER_MULTIPLIERS.keys()), index=1)
            completion = st.slider("Completion percentage", 0, 100, 25, 1)
            st.caption("Budget includes the chosen city and finish-tier multipliers.")
        submitted = st.form_submit_button("Calculate estimate", type="primary", use_container_width=True)
    if submitted:
        if area <= 0: st.error("Enter a built-up area greater than zero.")
        else:
            try: st.session_state["estimate_report"] = estimate_project(structure, area, city, tier, completion)
            except ValueError as exc: st.error(str(exc))
    report = st.session_state.get("estimate_report")
    if report:
        st.markdown("---")
        m1,m2,m3,m4 = st.columns(4)
        with m1: metric("Estimated budget", money(report["estimated_total_budget_inr"]))
        with m2: metric("Incurred cost", money(report["incurred_cost_inr"]))
        with m3: metric("Remaining", money(report["remaining_budget_inr"]))
        with m4: metric("Indicative property value", money(report["indicative_property_valuation_inr"]))
        st.markdown("### Project progress")
        st.progress(report["project_progress_percent"] / 100, text=f"{report['project_progress_percent']}% complete")
        left,right = st.columns([1,1])
        with left:
            st.markdown("### Material allowances")
            st.dataframe([{"Material": key, "Estimated quantity": f"{val['quantity']:,.1f} {val['unit']}"} for key,val in report["material_estimates"].items()], hide_index=True, use_container_width=True)
        with right:
            st.markdown("### Assumptions")
            assumptions = report["assumptions"]
            st.write(f"**Base construction rate:** ₹{assumptions['base_construction_rate_inr_per_sq_ft']:,}/sq ft")
            st.write(f"**City factor:** {assumptions['city_multiplier']} · **Tier factor:** {assumptions['property_tier_multiplier']}")
            st.caption(assumptions["budget_formula"].capitalize() + ". " + assumptions["materials_note"])
            st.caption(assumptions["valuation_note"])
        show_json_download("⬇ Download estimate JSON", report, "buildwise_project_estimate.json")

elif page == "Construction Assistant":
    section_header("Practical field guidance", "Construction Assistant", "Describe the task and select current weather for a focused checklist. For site-specific hazards, follow the site safety plan and competent-person direction.")
    with st.form("assistant_form"):
        task = st.text_area("What are you planning or concerned about?", placeholder="e.g., pouring a small slab tomorrow, scaffolding inspection, curing a new wall…", max_chars=700)
        col1,col2 = st.columns(2)
        with col1:
            weather = st.selectbox("Expected weather", ["Clear / dry", "Hot", "Rain", "High winds", "Cold", "Thunderstorm / lightning", "Dense fog / low visibility"])
        with col2:
            phase = st.selectbox("Project phase", ["Planning", "Earthworks", "Foundation", "Structure", "Masonry", "Finishing", "General site work"])
        submit = st.form_submit_button("Get guidance", type="primary", use_container_width=True)
    if submit:
        if len(task.strip()) < 8: st.error("Add a little more detail (at least 8 characters) so the guidance can be useful.")
        else:
            weather_advice = {
                "Clear / dry": ["Confirm water, shade and rest breaks are available.", "Control dust and maintain hydration.", "Secure materials and keep access routes clear."],
                "Hot": ["Schedule heavy work for cooler hours where practical.", "Provide shaded recovery, drinking water and heat-illness monitoring.", "Check concrete placement and curing plan against temperature and mix guidance."],
                "Rain": ["Reassess excavations, slopes, access and electrical protection.", "Cover materials and protect fresh concrete from runoff or washout.", "Pause work on slick elevated surfaces until safe footing is restored."],
                "High winds": ["Review crane, hoisting, scaffold and temporary-works wind limits.", "Secure sheet materials and loose objects; follow equipment manufacturer limits.", "Stop exposed lifting or work at height when site thresholds are reached."],
                "Cold": ["Check temperature limits for concrete, adhesives and coatings.", "Prevent icing and verify access, lighting and worker warm-up breaks.", "Use approved curing/protection methods; do not improvise heat sources."],
                "Thunderstorm / lightning": ["Stop crane, scaffold and exposed-height work; move to substantial shelter.", "Keep clear of open areas, metal equipment and isolated structures.", "Resume only after site lightning protocol gives the all-clear."],
                "Dense fog / low visibility": ["Pause vehicle movements or lifts if operators cannot see routes and signals clearly.", "Use trained banksmen and working lights; separate pedestrians from plant.", "Delay work at height if visibility makes edge or access hazards hard to judge."],
            }
            report = {"task": task.strip(), "phase": phase, "weather": weather, "generated_at_utc": datetime.now(timezone.utc).isoformat(), "scope_note": "General educational guidance; apply local regulations, approved method statements, manufacturer instructions and site-specific risk assessments."}
            st.session_state["assistant_report"] = report
    report = st.session_state.get("assistant_report")
    if report:
        st.markdown("---")
        st.markdown(f"### Guidance for: {report['phase']} · {report['weather']}")
        st.markdown("#### Start with the task")
        st.write(f"For **{report['task']}**, confirm the approved drawings and method statement, brief the crew, assign a competent supervisor, and check access, exclusion zones, PPE and emergency arrangements before work starts.")
        st.markdown("#### Weather advisory")
        advice = {
            "Clear / dry": ["Confirm water, shade and rest breaks are available.", "Control dust and maintain hydration.", "Secure materials and keep access routes clear."],
            "Hot": ["Schedule heavy work for cooler hours where practical.", "Provide shaded recovery, drinking water and heat-illness monitoring.", "Check concrete placement and curing plan against temperature and mix guidance."],
            "Rain": ["Reassess excavations, slopes, access and electrical protection.", "Cover materials and protect fresh concrete from runoff or washout.", "Pause work on slick elevated surfaces until safe footing is restored."],
            "High winds": ["Review crane, hoisting, scaffold and temporary-works wind limits.", "Secure sheet materials and loose objects; follow equipment manufacturer limits.", "Stop exposed lifting or work at height when site thresholds are reached."],
            "Cold": ["Check temperature limits for concrete, adhesives and coatings.", "Prevent icing and verify access, lighting and worker warm-up breaks.", "Use approved curing/protection methods; do not improvise heat sources."],
            "Thunderstorm / lightning": ["Stop crane, scaffold and exposed-height work; move to substantial shelter.", "Keep clear of open areas, metal equipment and isolated structures.", "Resume only after site lightning protocol gives the all-clear."],
            "Dense fog / low visibility": ["Pause vehicle movements or lifts if operators cannot see routes and signals clearly.", "Use trained banksmen and working lights; separate pedestrians from plant.", "Delay work at height if visibility makes edge or access hazards hard to judge."],
        }
        for item in advice[report["weather"]]: st.markdown(f"- {item}")
        st.markdown("#### Before work proceeds")
        for item in ["Check the relevant local code, permits and inspection hold points.", "Verify tools, equipment and temporary works are inspected and fit for use.", "Stop work and escalate if conditions differ from the approved plan."]:
            st.markdown(f"- {item}")
        st.caption(report["scope_note"])
        show_json_download("⬇ Download guidance JSON", report, "buildwise_construction_guidance.json")

st.markdown("---")
st.caption("BuildWise AI · Estimates and AI assessments are decision-support aids. Verify safety, engineering, code and valuation decisions with qualified professionals.")

# BuildWise AI

**AI-Powered Multimodal Construction Intelligence Platform** is a self-contained Streamlit capstone app for preliminary construction-site image review, crack triage, early-stage budgeting, real-estate valuation, and weather-aware guidance.

## Features

- **Site Safety & PPE Audit:** JPG/PNG upload, structured safety score, PPE checklist, hazards, severity, and corrective actions.
- **Structural Crack Analysis:** possible crack categories, severity, potential causes, repair next steps, and urgency. The app clearly states that AI results are preliminary and do not replace professional inspection.
- **Planning & Valuation:** structure type, square footage, city, property tier, and completion percentage produce INR budget, incurred and remaining cost, indicative quantities, progress, and property valuation with visible assumptions.
- **Construction Assistant:** task and phase guidance with a weather-specific safety advisory.
- **Reports:** download each result as JSON. No database is used.
- **Two image modes:** Gemini multimodal analysis when a server-side API key is configured; otherwise labelled deterministic demo outputs that never claim to analyze the uploaded image.

## Run locally

Use Python 3.10 or newer.

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Without a key, the app starts in **Demo mode**. The estimates and weather assistant work without Gemini.

To enable Gemini, configure `GEMINI_API_KEY` in Streamlit secrets (read first) or as a server environment variable (fallback), then restart Streamlit. The default multimodal model is `gemini-3.8-flash`; optionally override it with `GEMINI_MODEL`. The key stays server-side and is never displayed, returned in reports, or included in logs. Do not commit keys or `.streamlit/secrets.toml`. If no key is configured or Gemini cannot complete a request, the image modules return a clearly labelled fixed demo report that is not based on the uploaded image.

For a local Streamlit secrets file, create `.streamlit/secrets.toml` (already excluded by `.gitignore`):

```toml
GEMINI_API_KEY = "your-key-here"
# Optional:
GEMINI_MODEL = "gemini-3.8-flash"
```

Gemini image analysis uses Google's `google-genai` SDK and sends the uploaded image to Google's Gemini API. Follow the API's current terms and your organization's image/data handling rules.

## Deploy to Streamlit Community Cloud

1. Push this project to a GitHub repository. Confirm `.gitignore` excludes local secret files and never commit an API key.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), create an app from that repository and select `app.py` as the entry point.
3. In the app's **Settings → Secrets**, add:

   ```toml
   GEMINI_API_KEY = "your-key-here"
   # Optional model override:
   GEMINI_MODEL = "gemini-3.8-flash"
   ```

4. Save and let Streamlit rebuild from `requirements.txt`. A successful deployment must be confirmed in the Community Cloud app logs and live URL; this repository setup does not claim that deployment has been performed.

The app also supports setting `GEMINI_API_KEY` as an environment variable instead of a Streamlit secret. The optional model override is useful if model availability changes for your account.

## Estimate assumptions and limitations

Construction rates and property value rates are editable planning assumptions in `app.py`, not live market quotations. Material quantities use broad per-square-foot allowances and are not a bill of quantities. Budget excludes many site-specific factors such as soil, permits, taxes, professional fees, escalation, and detailed specifications. Valuation excludes land/title review and comparable sales. Validate estimates with current local quotations and qualified professionals.

Image outputs can miss or misinterpret visible conditions, especially where image quality, angle, lighting, occlusion, or scale is poor. Never use the app as a substitute for site inspection, engineered analysis, code compliance, or emergency response. If structural instability or immediate danger is suspected, keep people clear and contact qualified professionals/emergency services.

## Project files

- `app.py` — complete Streamlit UI, estimation logic, demo responses, and Gemini integration.
- `requirements.txt` — runtime dependencies.
- `.streamlit/config.toml` — upload limit and app theme.
- `.gitignore` — ignores environments, caches, and local secrets.

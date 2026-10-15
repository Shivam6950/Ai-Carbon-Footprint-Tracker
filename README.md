# Carbon Footprint Tracker (Streamlit)

A browser-based version of the original Tkinter Carbon Footprint Tracker. It includes household inputs, estimated monthly emissions, comparison charts, a category breakdown, and optional AI sustainability advice via the OpenAI API.

## Run locally

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

To enable AI advice locally, create `.streamlit/secrets.toml` (this file is git-ignored) with:

```toml
OPENAI_API_KEY = "your-real-api-key"
```

Optional model override: set `OPENAI_MODEL` in your environment. The default is `gpt-4o-mini`.

## Deploy to Streamlit Community Cloud

1. Create a new GitHub repository, for example `carbon-footprint-tracker`.
2. Upload `app.py`, `requirements.txt`, `README.md`, `.gitignore`, and `.streamlit/config.toml`. Do **not** upload `.streamlit/secrets.toml` or any real API key.
3. Open https://share.streamlit.io/ and sign in with GitHub.
4. Choose **Create app**, select your repository and branch (usually `main`), and set the app file path to `app.py`.
5. In the app's **Settings / Secrets**, add:
   ```toml
   OPENAI_API_KEY = "your-real-api-key"
   ```
6. Deploy. Streamlit will install dependencies from `requirements.txt` and provide a public URL.
7. Open the live URL in a private/incognito window to verify it works without your local machine.

## API key safety

- Never commit API keys to GitHub or put them directly in `app.py`.
- Use Streamlit's Secrets settings for the hosted app.
- API calls may incur charges; configure usage limits with your API provider.
- If the key is absent, the calculator and charts still work, and the app displays a setup message for the AI advisor.

## Notes about the estimates

Emission factors are simplified assumptions inherited from the source project. The AC-hours input is collected for context in the AI prompt but does not independently change the emissions calculation. Results should be treated as estimates, not an official carbon audit.

# 🧭 OpportunityScout AI Agent

OpportunityScout is an agentic web application that helps students discover and act on real opportunities such as workshops, hackathons, internships, fellowships, scholarships, and tech programs.

It is **not just a chatbot**. It performs a multi-step workflow:

1. Understands the user's constraints.
2. Searches the live web using **Anakin Search API**.
3. Deduplicates and scores the results against location, student eligibility, cost, and relevance.
4. Reads a selected live page using **Anakin URL Scraper**.
5. Can deep-compare a shortlist using **Anakin Agentic Search**.
6. Uses **Anakin Wire** to generate a tailored application pack.
7. Takes concrete action by exporting the shortlist to CSV, generating `.ics` calendar reminders, and linking directly to source/application pages.

## Why Anakin is central to this project

This project uses Anakin as its web/action layer instead of relying on stale LLM knowledge.

### 1. Search API
`POST /v1/search`

Used to find current opportunities and return structured source results containing titles, URLs, snippets, and dates when available.

### 2. URL Scraper
`POST /v1/url-scraper`

Used when the user asks the agent to read an opportunity page. This lets the agent retrieve current page content instead of pretending it already knows what the page says.

### 3. Agentic Search
`POST /v1/agentic-search`

Used for deeper multi-source comparison. Anakin handles query refinement, source discovery, citation scraping, and synthesis.

### 4. Wire
`POST /v1/wire/task`

Used to run the `chatgpt` Wire action for generating an application action pack without requiring the user to configure a second AI provider key.

Together these components let the app **search → read → reason → compare → act**.

## Tech stack

- Python
- Streamlit
- Anakin.io REST APIs
- Requests
- Pandas

## Project structure

```text
opportunityscout-agent/
├── app.py
├── agent.py
├── anakin_client.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Run locally

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/opportunityscout-agent.git
cd opportunityscout-agent
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your Anakin key

Copy:

```bash
copy .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
ANAKIN_API_KEY=ak-your-real-key
ANAKIN_BASE_URL=https://api.anakin.io/v1
```

Never commit `.env`.

### 5. Start the app

```bash
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub.
2. Open https://share.streamlit.io/
3. Click **Create app**.
4. Select your repository and the `main` branch.
5. Set the main file to `app.py`.
6. Open **Advanced settings / Secrets**.
7. Add:

```toml
ANAKIN_API_KEY = "ak-your-real-key"
```

8. Deploy.

Your deployed URL will look similar to:

```text
https://your-app-name.streamlit.app
```

## Security

- API keys are read from `.env` locally or Streamlit Secrets in production.
- `.env` and `.streamlit/secrets.toml` are ignored by Git.
- The application does not hard-code credentials.

## Suggested demo

A good 2–3 minute demo:

1. Search for: `AI / cloud workshops`, location `Hyderabad / India`, timeframe `next 60 days`.
2. Show the agent returning live source results.
3. Open one result with **Read this page with Anakin**.
4. Click **Build application pack**.
5. Download the CSV.
6. Download an `.ics` reminder.
7. Optionally show **Deep-compare my results**.
8. Briefly show `anakin_client.py` in GitHub to prove the integration.

## Future improvements

- Anakin Browser API for controlled form-filling on supported application pages.
- Anakin Wire write actions for direct workflow execution where credentials/consent are available.
- Deadline extraction into exact calendar dates.
- Saved user profiles for eligibility checks.
- Automated monitoring for newly announced opportunities.

## License

MIT

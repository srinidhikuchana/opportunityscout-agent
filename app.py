import os
from textwrap import shorten

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from agent import (
    build_search_prompt,
    csv_bytes,
    make_ics,
    normalize_results,
    rank_results,
)
from anakin_client import AnakinClient, AnakinError

load_dotenv()

st.set_page_config(
    page_title="OpportunityScout AI",
    page_icon="🧭",
    layout="wide",
)

st.title("🧭 OpportunityScout AI Agent")
st.caption(
    "A live-web agent that discovers opportunities, reads sources, compares options, "
    "reasons about fit, and turns results into an actionable shortlist."
)

with st.sidebar:
    st.header("Your search")
    opportunity_type = st.selectbox(
        "Opportunity type",
        ["Workshops & events", "Hackathons", "Internships", "Fellowships", "Scholarships", "Tech programs"],
    )
    interests = st.text_input("Interests", "AI, software engineering, cloud, developer tools")
    location = st.selectbox("Location", ["Hyderabad / India", "Remote / Online", "India", "Worldwide"])
    timeframe = st.text_input("Timeframe", "next 60 days")
    only_free = st.checkbox("Prefer free opportunities", value=True)
    student_only = st.checkbox("Prefer student-eligible opportunities", value=True)
    result_limit = st.slider("Results", 5, 15, 8)
    run_search = st.button("🔎 Run agent", type="primary", use_container_width=True)

    st.divider()
    st.markdown("**Powered by Anakin**")
    st.caption("Search API • URL Scraper • Agentic Search • Wire")

api_key = ""
try:
    api_key = st.secrets.get("ANAKIN_API_KEY", "")
except Exception:
    pass
api_key = api_key or os.getenv("ANAKIN_API_KEY", "")

if not api_key:
    st.info(
        "Add `ANAKIN_API_KEY` to `.env` locally or to Streamlit Community Cloud → "
        "App settings → Secrets. Your key is never committed to GitHub."
    )

if "ranked" not in st.session_state:
    st.session_state.ranked = []

if run_search:
    if not api_key:
        st.error("Please configure ANAKIN_API_KEY first.")
        st.stop()

    prompt = build_search_prompt(
        opportunity_type, interests, location, timeframe, only_free, student_only
    )

    try:
        client = AnakinClient(api_key=api_key)

        with st.status("Agent is working...", expanded=True) as status:
            st.write("1. Planning the live-web search")
            st.code(prompt, language=None)

            st.write("2. Asking Anakin Search for current sources")
            raw = client.search(prompt, limit=result_limit)

            st.write("3. Normalizing, deduplicating, and scoring candidates")
            items = normalize_results(raw)
            ranked = rank_results(items, location, only_free, student_only)
            st.session_state.ranked = ranked
            st.session_state.last_prompt = prompt

            status.update(label=f"Done — found {len(ranked)} candidates", state="complete")

    except AnakinError as e:
        st.error(str(e))
    except Exception as e:
        st.exception(e)

ranked = st.session_state.ranked

if ranked:
    st.subheader("Best matches")

    top_cols = st.columns(3)
    top_cols[0].metric("Candidates", len(ranked))
    top_cols[1].metric("Best match", f"{ranked[0]['match_score']}%")
    official_like = sum(1 for x in ranked if x.get("domain"))
    top_cols[2].metric("Source links", official_like)

    table = pd.DataFrame(
        [
            {
                "Match": f"{x['match_score']}%",
                "Opportunity": x["title"],
                "Source": x["domain"],
                "Date": x["date"] or "Check source",
            }
            for x in ranked
        ]
    )
    st.dataframe(table, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Download shortlist CSV",
        data=csv_bytes(ranked),
        file_name="opportunityscout_shortlist.csv",
        mime="text/csv",
    )

    st.divider()

    for i, item in enumerate(ranked, start=1):
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"### {i}. {item['title']}")
                st.caption(f"{item['domain']} • Match {item['match_score']}%")
                if item["snippet"]:
                    st.write(shorten(item["snippet"], width=500, placeholder="…"))
                if item["url"]:
                    st.link_button("Open official/source page ↗", item["url"])
            with c2:
                st.download_button(
                    "📅 Reminder",
                    data=make_ics(
                        item["title"],
                        item["url"],
                        "OpportunityScout reminder. Verify the official deadline/date before applying.",
                    ),
                    file_name=f"opportunity_{i}.ics",
                    mime="text/calendar",
                    key=f"ics_{i}",
                    use_container_width=True,
                )

            detail_col, pack_col = st.columns(2)

            with detail_col:
                if st.button("📖 Read this page with Anakin", key=f"read_{i}", use_container_width=True):
                    try:
                        client = AnakinClient(api_key=api_key)
                        with st.spinner("Anakin is reading the live page..."):
                            page = client.scrape(item["url"], use_browser=False)
                        text = (
                            page.get("markdown")
                            or page.get("content")
                            or page.get("cleanedHtml")
                            or str(page)
                        )
                        st.text_area("Live page content", text[:12000], height=280, key=f"text_{i}")
                    except Exception as e:
                        st.error(str(e))

            with pack_col:
                if st.button("✨ Build application pack", key=f"pack_{i}", use_container_width=True):
                    try:
                        client = AnakinClient(api_key=api_key)
                        prompt = f"""
You are an application assistant. Based only on the opportunity information below,
create a concise action pack for a college engineering student.

Opportunity: {item['title']}
URL: {item['url']}
Known information: {item['snippet']}

Return:
1. Why this opportunity is worth considering
2. Eligibility/checklist items to verify
3. A 100-150 word application motivation draft
4. A practical 5-step application plan
5. Any facts that MUST be verified on the official page

Do not invent dates, eligibility, fees, or benefits that are not in the supplied information.
"""
                        with st.spinner("Anakin Wire is generating the action pack..."):
                            answer = client.ask_chatgpt_via_wire(prompt)
                        st.markdown(answer)
                    except Exception as e:
                        st.error(str(e))

    st.divider()
    st.subheader("Deep research mode")
    st.write(
        "For the strongest 2–3 choices, Anakin can run a multi-stage research job that "
        "searches, scrapes citations, and synthesizes a deeper comparison."
    )
    if st.button("🧠 Deep-compare my results"):
        try:
            client = AnakinClient(api_key=api_key)
            shortlist = "\n".join(
                f"- {x['title']}: {x['url']}" for x in ranked[:5]
            )
            prompt = f"""
Compare these opportunities for an undergraduate engineering student interested in {interests}.
Prioritize eligibility, credibility, learning value, cost, timing, and concrete career value.
Use live sources. Clearly mark unknowns and recommend the best 3 with reasons.

{shortlist}
"""
            with st.spinner("Running Anakin Agentic Search..."):
                result = client.agentic_research(prompt)
            report = (
                result.get("answer")
                or result.get("report")
                or result.get("markdown")
                or result.get("generatedJson")
                or result.get("result")
                or result
            )
            st.markdown(report if isinstance(report, str) else f"```json\n{report}\n```")
        except Exception as e:
            st.error(str(e))

else:
    st.markdown(
        """
### What this agent actually does

1. **Browses the live web** through Anakin Search.
2. **Reads source pages** through Anakin URL Scraper.
3. **Reasons and ranks** results against your constraints.
4. **Deep-researches** a shortlist through Anakin Agentic Search.
5. **Takes action** by creating a CSV shortlist, calendar reminders, direct application links,
   and tailored application packs through Anakin Wire.

Use the sidebar and click **Run agent**.
"""
    )

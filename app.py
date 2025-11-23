import streamlit as st
from evaluate_intro import score_transcript

st.set_page_config(page_title="Transcript Rubric Scorer", layout="centered")

st.title("Transcript Rubric Scorer")
st.write("Paste a self-introduction transcript and get rubric-based scoring with feedback.")

transcript = st.text_area("Transcript", height=250, placeholder="Paste transcript here...")
duration = st.number_input("Duration (seconds)", min_value=0.0, value=0.0, help="Leave 0 if unknown; tool will assume ideal WPM.")

if st.button("Score"):
    dur = None if duration <= 0 else duration
    result = score_transcript(transcript, dur)
    st.subheader(f"Overall Score: {result['overall_score']}")
    cols = st.columns(3)
    cols[0].metric("Words", result["words"])
    cols[1].metric("Sentences", result["sentences"])
    cols[2].metric("WPM", result["wpm"])

    st.markdown("---")
    st.subheader("Per-criterion details")
    for c in result["criteria"]:
        with st.expander(f"{c['name']} (weight {c['weight']}) — score {c['score']}"):
            st.write(c["feedback"])
            extra = {k: v for k, v in c.items() if k not in ["name", "weight", "score", "feedback"]}
            if extra:
                st.json(extra)

st.markdown("---")
st.caption("This is a rule-based + NLP hybrid scorer aligned with the provided rubric.")

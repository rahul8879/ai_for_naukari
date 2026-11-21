import streamlit as st
from ai_sharks.backends import OpenAIBackend
from ai_sharks.graph import stream_panel
from ai_sharks.schema import MAX_PITCH_CHARS, validate_pitch
from ai_sharks.sharks import SHARKS
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent

SAMPLES = {
    "TiffinAI — meal subscriptions": HERE / "sample_pitch.txt",
    "FleetShift — strong numbers": HERE / "sample_pitches/fleetshift.txt",
    # "VibeVerse — hype, little traction": HERE / "sample_pitches/vibeverse.txt",
    "GharSolar — vision vs margins": HERE / "sample_pitches/gharsolar.txt",
}


def load_selected_sample() -> None:
    st.session_state["pitch"] = SAMPLES[st.session_state["sample"]].read_text(encoding="utf-8")



def render_verdicts(verdicts, previous=None) -> None:
    previous = {v.shark: v for v in previous or []}
    for v in verdicts:
        with st.container(border=True):
            st.subheader(f"{v.shark} · {v.stance}")
            if v.shark in previous:
                st.caption(f"Round one: {previous[v.shark].stance} → Final: {v.stance}")
            if v.offer:
                st.write(f"Offer: {v.offer}")
            st.write(v.reasoning)


def main() -> None:
    st.set_page_config(page_title="Pitch to the AI Sharks", page_icon="🦈", layout="wide")
    st.title("🦈 Pitch to the AI Sharks")
    st.write("Pitch your startup. Hear three perspectives. Learn what to improve.")

    with st.sidebar:
        st.selectbox("Example pitch", list(SAMPLES), key="sample", on_change=load_selected_sample)
        st.subheader("Meet the investors")
        for shark in SHARKS:
            st.write(f"**{shark.name}** — {shark.title}")

    if "pitch" not in st.session_state:
        load_selected_sample()
    with st.form("pitch_form"):
        st.text_area("Your startup pitch", key="pitch", height=260, max_chars=MAX_PITCH_CHARS)
        submitted = st.form_submit_button("Face the Sharks", type="primary")

    if submitted:
        st.session_state.pop("result", None)
        try:
            pitch = validate_pitch(st.session_state["pitch"])
            backend = OpenAIBackend()
            result = {"pitch": pitch}
            with st.status("The investors are evaluating your pitch…", expanded=True) as status:
                labels = {"panel": "Initial verdicts ready", "debate": "Debate complete", "host": "Host summary ready"}
                for event in stream_panel(pitch, backend):
                    for node, update in event.items():
                        result.update(update)
                        st.write(labels[node])
                status.update(label="Panel complete", state="complete", expanded=False)
            st.session_state["result"] = result
        except (ValueError) as exc:
            st.error(str(exc))

    if "result" in st.session_state:
        result = st.session_state["result"]
        st.caption("Results from the last successful OpenAI run")
        with st.expander("Pitch evaluated in this run"):
            st.text(result["pitch"])
        initial, final = st.tabs(["Round one", "After debate"])
        with initial:
            render_verdicts(result["round1"])
        with final:
            render_verdicts(result["final"], result["round1"])
        st.subheader("🎤 Host's takeaway")
        st.write(result["summary"])
        payload = {
            **result,
            "round1": [v.model_dump() for v in result["round1"]],
            "final": [v.model_dump() for v in result["final"]],
        }
        st.download_button(
            "Download results (JSON)", json.dumps(payload, indent=2, ensure_ascii=False),
            file_name="ai_sharks_result.json", mime="application/json",
        )


if __name__ == "__main__":
    main()







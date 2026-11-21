from langgraph.graph import END, START, StateGraph
from .schema import Verdict, validate_pitch
from .sharks import SHARKS
from typing import TypedDict
from .backends import Backend
from collections.abc import Iterator



class State(TypedDict):
    pitch: str
    round1: list[Verdict]
    final: list[Verdict]
    summary: str


def build_panel(backend: Backend):

    def panel(state: State) -> dict:
        pitch = validate_pitch(state["pitch"])
        verdicts = [backend.evaluate(shark, pitch, ()) for shark in SHARKS]
        return {"pitch": pitch, "round1": verdicts}
    
    def debate(state: State) -> dict:
        
        final = []
        for shark in SHARKS:
            others = tuple(v for v in state["round1"] if v.shark != shark.name)
            final.append(backend.evaluate(shark, state["pitch"], others))
        return {"final": final}
    

    def host(state: State) -> dict:
        summary = backend.summarize(state["pitch"], state["round1"], state["final"])
        return {"summary": summary}
    

    graph = StateGraph(State)
    graph.add_node("panel", panel)
    graph.add_node("debate", debate)
    graph.add_node("host", host)
    graph.add_edge(START, "panel")
    graph.add_edge("panel", "debate")
    graph.add_edge("debate", "host")
    graph.add_edge("host", END)
    return graph.compile()


def run_panel(pitch: str, backend: Backend) -> State:
    return build_panel(backend).invoke({"pitch": validate_pitch(pitch)})


def stream_panel(pitch: str, backend: Backend) -> Iterator[dict]:
    yield from build_panel(backend).stream(
        {"pitch": validate_pitch(pitch)}, stream_mode="updates"
    )

import json
import operator
import os
import time
from typing import Annotated, Literal, TypedDict
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from pydantic import BaseModel, Field
from .analytics import sales, inventory, finance, validate_scope
from langchain.agents import create_agent


SPECIALISTS = ("sales", "inventory", "finance")

class AnalysisState(TypedDict, total=False):
    question: str
    region: str
    month: str
    selected: list[str]
    routing_reason: str
    findings: Annotated[list[dict], operator.add]
    answer: str
    recommendations: list[str]
    llm_used: bool


class RouteDecision(BaseModel):
    agents: list[Literal["sales", "inventory", "finance"]] = Field(min_length=1)
    reason: str


class FinalAssessment(BaseModel):
    answer: str = Field(description="Fact-grounded executive summary; avoid causal certainty")
    recommendations: list[str] = Field(description="Concrete verification or improvement steps")


def model():
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not configured. This classroom project requires a real LLM.")
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), temperature=0)



@tool
def get_sales_metrics(region: str, month: str) -> str:
    """Return verified revenue, units, and product-level month-on-month sales metrics."""
    validate_scope(region, month)
    return json.dumps(sales(region, month))

@tool
def get_inventory_metrics(region: str, month: str) -> str:
    """Return verified product stockout-days and inventory signals for region and month."""
    validate_scope(region, month)
    return json.dumps(inventory(region, month))

@tool
def get_finance_metrics(region: str, month: str) -> str:
    """Return verified gross margin, COGS and promotion spend for region and month."""
    validate_scope(region, month)
    return json.dumps(finance(region, month))


TOOL_BY_SPECIALIST = {"sales": get_sales_metrics, "inventory": get_inventory_metrics, "finance": get_finance_metrics}
DATA_BY_SPECIALIST = {"sales": sales, "inventory": inventory, "finance": finance}




def run_specialist(name: str, question: str, region: str, month: str) -> dict:
    selected_tool = TOOL_BY_SPECIALIST[name]
    agent = create_agent(
        model=model(),
        tools=[selected_tool],
        system_prompt=(
            f"You are the {name.upper()} analyst of a retail enterprise. "
            f"You MUST call {selected_tool.name} with the provided region and month before answering. "
            "Use only the tool's figures. Report exact metrics and avoid invented explanations. "
            "Differentiate observable correlations from proven causes. Keep your response concise."
        ),
    )

    result = agent.invoke({"messages": [{"role": "user", "content": f"Question: {question}\nRegion: {region}\nMonth: {month}"}]})
    tool_calls = [c for m in result["messages"] for c in (getattr(m, "tool_calls", None) or [])]
    if not tool_calls:
        raise RuntimeError(f"{name} agent did not call its required tool. No answer returned.")
    return {"agent": name, "analysis": str(result["messages"][-1].content),
            "data": DATA_BY_SPECIALIST[name](region, month), "tool_calls": len(tool_calls)}



def supervisor(state: AnalysisState):
    decision = model().with_structured_output(RouteDecision).invoke(
        "You are an enterprise analytics supervisor. Choose the minimum set of specialists "
        "required for the user's question. Sales handles revenue and units; inventory handles stockouts; "
        "finance handles gross profit, margin, and promotion spend. For a broad WHY revenue changed "
        "question, use all three to investigate alternative hypotheses. Never invent business data. "
        f"Question: {state['question']}"
    )
    selected = [name for name in SPECIALISTS if name in decision.agents]
    return {"selected": selected, "routing_reason": decision.reason}



def dispatch(state: AnalysisState):
    return [Send(name, {"question": state["question"], "region": state["region"], "month": state["month"]})
            for name in state["selected"]]


def make_worker(name):
    def worker(state: dict):
        return {"findings": [run_specialist(name, state["question"], state["region"], state["month"])]}
    return worker



def synthesis(state: AnalysisState):
    facts = [{"agent": f["agent"], "data": f["data"], "analysis": f["analysis"]} for f in state["findings"]]
    result = model().with_structured_output(FinalAssessment).invoke(
        "You are a cautious retail decision support analyst. Use ONLY the JSON evidence below. "
        "Answer the question, cite exact numbers, and distinguish a hypothesis from a proven cause. "
        "Stockout-days cannot alone prove the amount of lost sales. Recommend verification steps. "
        "Do not infer demand, customer traffic, or competitor activity as facts without data. "
        f"Question: {state['question']}\nEvidence:\n{json.dumps(facts)}"
    )
    return {"answer": result.answer, "recommendations": result.recommendations, "llm_used": True}



def build_graph():
    g = StateGraph(AnalysisState)
    g.add_node("supervisor", supervisor)
    for name in SPECIALISTS:
        g.add_node(name, make_worker(name))
    g.add_node("synthesis", synthesis)
    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", dispatch, list(SPECIALISTS))
    for name in SPECIALISTS:
        g.add_edge(name, "synthesis")
    g.add_edge("synthesis", END)
    return g.compile()




GRAPH = build_graph()




def analyze(question: str, region: str, month: str):
    validate_scope(region, month)
    start = time.perf_counter()
    result = GRAPH.invoke({"question": question, "region": region, "month": month, "findings": []},
                          config={"recursion_limit": 25})
    result["duration_ms"] = round(1000 * (time.perf_counter() - start))
    result["findings"] = sorted(result["findings"], key=lambda x: SPECIALISTS.index(x["agent"]))
    return result










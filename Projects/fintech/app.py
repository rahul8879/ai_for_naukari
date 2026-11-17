from tools import get_loan_status, get_emi_schedule,process_refund_request,calculate_prepayment
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from typing import Optional
load_dotenv()
from rag_chain import rag_answer

from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o-mini")


# step 1 :
# create the list of tools --> agent
tools = [get_loan_status, get_emi_schedule, process_refund_request, calculate_prepayment]

llm_with_tools = llm.bind_tools(tools)


tool_map = {
    "get_loan_status": get_loan_status,
    "get_emi_schedule": get_emi_schedule,
    "process_refund_request": process_refund_request,
    "calculate_prepayment": calculate_prepayment
}


ROUTER_PROMPT = """
You are a query classifier for Bajaj Finance helpdesk.

Classify the customer query into ONE of these categories:
- "tool"   : query requires live loan data (needs Loan ID like BFL001)
              Examples: loan status, EMI schedule, prepayment, refund,
              foreclose my loan, close my loan, settle my account
- "policy" : query is about rules, eligibility, charges, documents
              AND follow-up questions about a previous policy answer
              Examples: CIBIL score, foreclosure charges, interest rates,
              documents needed, what happens if I miss EMI,
              "how do you know this", "where did you get this",
              "is this from your policy", "what is your source"
- "general": greeting, thank you, out of scope

Reply with ONLY one word: tool / policy / general
"""


def classify_query(query):
    response = llm.invoke([
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=query),
    ])
    category = response.content.strip()
    if category not in ["tool", "policy", "general"]:
        raise ValueError(f"Invalid category: {category}")
    return category

# print(classify_query('how I can get personal loan'))





SYSTEM_PROMPT = """You are a professional Bajaj Finance customer support agent.

You have access to:
1. TOOLS  — for live loan data (status, EMI, prepayment, refund)
             Use when customer provides a Loan ID (BFL + digits)
2. POLICY — handled separately via knowledge base

RULES:
- Loan ID present → use tools
- Format all amounts with Rs and commas (e.g., Rs 8,450)
- Be warm, concise, and professional
- If a loan is not found, ask customer to double-check the Loan ID
"""


store = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    """Return existing chat history or create a new one for this session."""
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]


def run_chat_turn(user_message:str,session_id):
    history = get_session_history(session_id)
    messages = [{'role':"system","content":SYSTEM_PROMPT}]
    messages.extend(history.messages)
    messages.append(HumanMessage(content=user_message))
    tools_used = []

    response = llm_with_tools.invoke(messages)

    while response.tool_calls:
        messages.append(response)
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tools_used.append(tool_name)

            tool_fn = tool_map.get(tool_name)
            if tool_fn:
                result = tool_fn.invoke(tool_args)
            else:
                result = {"error":"tool is not available"}

            messages.append(ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"]

            ))
        response = llm_with_tools.invoke(messages)

    history.add_user_message(user_message)
    history.add_ai_message(response.content)

    return response.content, tools_used


def run_policy_run(user_message:str,session_id):
    history = get_session_history(session_id)
    print(history.messages)
    # policy_history = [msg for msg in history.messages if msg.role in ['human','ai']]
    policy_history = history.messages
    reply = rag_answer(user_message,policy_history)
    history.add_user_message(user_message)
    history.add_ai_message(reply)
    return reply


def run_general_turn(user_message:str,session_id):
    history = get_session_history(session_id)
    message = [{'role':"system","content":SYSTEM_PROMPT}]
    message.extend(history.messages)
    message.append(HumanMessage(content=user_message))
    response = llm.invoke(message)
    history.add_user_message(user_message)
    history.add_ai_message(response.content)
    return response.content
    

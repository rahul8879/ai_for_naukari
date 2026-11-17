from datetime import datetime, date
from langchain_core.tools import tool

import json
import uuid



DB_PATH = "db.json"

with open(DB_PATH, "r") as f:
    db = json.load(f)


@tool
def get_loan_status(loan_id: str) -> dict:
    """Fetches current loan status from Bajaj Finance database.

    Returns EMI amount, remaining tenure, outstanding balance,
    and next due date for the given loan account.

    Use this when the customer asks about their loan details,
    EMI, balance, or tenure.

    Args:
        loan_id: The loan account number (e.g., 'BFL2024001')
    """
    loan_id = loan_id.strip().upper()

    if loan_id not in db["loans"]:
        return {"error": f"Loan {loan_id} not found in our system. Please check the loan account number."}

    loan = db["loans"][loan_id]
    return {
        "loan_id":           loan_id,
        "customer_name":     loan["customer_name"],
        "loan_type":         loan["loan_type"],
        "emi_amount":        loan["emi"],
        "remaining_months":  loan["remaining_months"],
        "outstanding_balance": loan["outstanding_balance"],
        "next_due_date":     loan["next_due_date"],
        "interest_rate":     loan["interest_rate"],
        "total_tenure":      loan["tenure_months"],
    }




@tool
def get_emi_schedule(loan_id: str) -> dict:
    """Returns the upcoming EMI schedule (next 6 months) for a loan.

    Use this when the customer asks about their payment schedule,
    upcoming EMI dates, or future dues.

    Args:
        loan_id: The loan account number (e.g., 'BFL2024001')
    """
    loan_id = loan_id.strip().upper()

    if loan_id not in db["loans"]:
        return {"error": f"Loan {loan_id} not found."}

    loan = db["loans"][loan_id]
    emi = loan["emi_amount"]
    next_due = datetime.strptime(loan["next_due_date"], "%Y-%m-%d")

    schedule = []
    for i in range(min(6, loan["remaining_months"])):
        month = (next_due.month + i - 1) % 12 + 1
        year  = next_due.year + (next_due.month + i - 1) // 12
        due_date = date(year, month, next_due.day)
        schedule.append({
            "installment_no": loan["paid_months"] + i + 1,
            "due_date":       str(due_date),
            "amount":         emi,
        })

    return {
        "loan_id":          loan_id,
        "customer_name":    loan["customer_name"],
        "emi_amount":       emi,
        "remaining_months": loan["remaining_months"],
        "upcoming_schedule": schedule,
    }


@tool
def calculate_prepayment(loan_id: str, prepay_amount: float) -> dict:
    """Calculates prepayment penalty and net financial benefit for a loan.

    Use this when the customer asks about foreclosure, prepayment charges,
    or wants to know if making a prepayment is financially worth it.

    Args:
        loan_id:       The loan account number (e.g., 'BFL2024001')
        prepay_amount: Amount in ₹ the customer wants to prepay
    """
    loan_id = loan_id.strip().upper()

    if loan_id not in db["loans"]:
        return {"error": f"Loan {loan_id} not found."}

    loan        = db["loans"][loan_id]
    outstanding = loan["outstanding_balance"]
    rate        = loan["interest_rate"]
    remaining   = loan["remaining_months"]

    if prepay_amount > outstanding:
        return {
            "error":       f"Prepayment ₹{prepay_amount:,.0f} exceeds outstanding ₹{outstanding:,.0f}.",
            "max_prepay":  outstanding,
        }

    # 4% penalty if paid within first 3 years, 2% after
    charge_pct    = 4.0 if loan["paid_months"] < 36 else 2.0
    penalty       = prepay_amount * charge_pct / 100
    interest_saved = prepay_amount * (rate / 12 / 100) * remaining

    return {
        "loan_id":              loan_id,
        "prepay_amount":        prepay_amount,
        "penalty_percent":      charge_pct,
        "penalty_amount":       round(penalty, 2),
        "interest_saved":       round(interest_saved, 2),
        "net_benefit":          round(interest_saved - penalty, 2),
        "total_to_pay":         round(prepay_amount + penalty, 2),
        "is_full_foreclosure":  prepay_amount >= outstanding,
        "recommendation":       (
            "Prepayment is financially beneficial."
            if interest_saved > penalty else
            "Interest saved is less than penalty. Consider waiting."
        ),
    }


@tool
def process_refund_request(loan_id: str, reason: str, amount: float) -> dict:
    """Raises a refund request for a customer (excess EMI, double deduction, etc).

    Use this when the customer explicitly asks to raise a refund,
    file a dispute, or report a wrong deduction.

    Args:
        loan_id: The loan account number (e.g., 'BFL2024001')
        reason:  Reason for the refund request
        amount:  Amount in ₹ the customer is claiming as refund
    """
    loan_id = loan_id.strip().upper()

    if loan_id not in db["loans"]:
        return {"error": f"Loan {loan_id} not found."}

    ticket_id = "REF" + str(uuid.uuid4())[:8].upper()

    # you can store this ticket to json files --> send it to support team via email ??
    # SMTP --> you can easily 

    return {
        "success":             True,
        "ticket_id":           ticket_id,
        "loan_id":             loan_id,
        "customer_name":       db["loans"][loan_id]["customer_name"],
        "amount_claimed":      amount,
        "reason":              reason,
        "status":              "Raised",
        "expected_resolution": "5–7 working days",
        "message":             f"Your refund request has been logged. Ticket ID: {ticket_id}",
    }

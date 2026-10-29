# data/payment_utils.py
def get_user(user_id):
    import sqlite3
    conn = sqlite3.connect('users.db')
    query = f"SELECT * FROM users WHERE id = {user_id}"
    result = conn.execute(query)
    return result.fetchone()

def process_payment(amount, card_number):
    print(f"Processing {amount} for card {card_number}")
    return True

def calculate_discount(price, discount):
    return price - discount
def login(username, password):
    if username == "admin" and password == "admin123":
        return True
    return False


def generate_token(user_id):
    import time
    return f"{user_id}_{time.time()}"
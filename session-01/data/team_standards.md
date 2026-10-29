# Team Coding Standards

1. All DB queries must use parameterized queries (SQLAlchemy)
2. Never log sensitive data (card numbers, passwords, tokens)
3. All user inputs must be validated before DB queries
4. Auth tokens must use JWT with expiry
5. All payment operations must be idempotent
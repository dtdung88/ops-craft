import re


def check_password_strength(password: str) -> tuple[bool, List[str]]:
    """
    Check password strength
    Returns: (is_strong, list_of_issues)
    """
    issues = []
    
    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    
    if not re.search(r'[a-z]', password):
        issues.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'[A-Z]', password):
        issues.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'\d', password):
        issues.append("Password must contain at least one number")
    
    # Optional: special characters
    # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
    #     issues.append("Password should contain at least one special character")
    
    return len(issues) == 0, issues
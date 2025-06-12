def code_to_str(var: str) -> str:
    """Convert code format to display string format."""
    str_var = var.replace("_", " ")
    str_var = str.title(str_var)
    return str_var


def str_to_code(var: str) -> str:
    """Convert display string to code format."""
    code_var = var.replace(" ", "_")
    code_var = code_var.lower()
    return code_var

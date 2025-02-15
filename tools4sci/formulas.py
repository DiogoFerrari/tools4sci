import re

__all__ = ['extract_variables']

def extract_variables(formula):
    """
    Extracts all unique variable names from a formula string.

    Parameters:
    ----------
    formula : str
         The formula string (e.g., 'y ~ x1 + x2*x3 + log(x4) + C(x5)').

    Returns:
    -------
        variables (set): A set of unique variable names.
    """
    # Remove transformation functions like log(), C(), etc.
    cleaned_formula = re.sub(r'[a-zA-Z_]+\((.*?)\)', r'\1', formula)
    
    # Split the formula into LHS and RHS
    lhs, rhs = cleaned_formula.split('~')
    
    # Extract all variable names (words) while ignoring operators like *, +, ~, etc.
    variables = set(re.findall(r'\b\w+\b', lhs + " " + rhs))
    
    d = {
        'formula' : formula,
        'lhs': lhs,
        'rhs': rhs,
        'variables':variables
         }
    return d

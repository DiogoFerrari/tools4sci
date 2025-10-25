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
        dict with lhs, rhs, interactions, and terms
    """
    lhs, rhs = formula.split('~')
    lhs = lhs.strip()
    rhs = rhs.strip()

    # collect terms in the rhs
    all_terms = []
    terms = re.split(r'\s*\+\s*', rhs)
    for term in terms:
        # Split on '*' to get interactions
        interactions = re.split(r'\s*\*\s*', term)
        all_terms.extend(interactions)
    all_terms = list(set(term.strip() for term in all_terms if term.strip()))
    
    # collect interactions
    interactions = []
    terms = rhs.split('+')
    for term in terms:
        if '*' in term:
            interactions.append(term.strip())
    
    return {'lhs':lhs, 'rhs':rhs,
            "interactions":interactions, 'terms':all_terms}

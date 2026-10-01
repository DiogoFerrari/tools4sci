import re
import io
import keyword
import tokenize

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
        dict with lhs, rhs, interactions, terms, and variables.
        variables contains unique variable names from both sides in order of
        first appearance, excluding function names, literals, and keyword labels.
    """
    lhs, rhs = formula.split('~')
    lhs = lhs.strip()
    rhs = rhs.strip()

    tokens = [token for token in tokenize.generate_tokens(io.StringIO(formula).readline)
              if token.type not in (tokenize.NL, tokenize.NEWLINE,
                                    tokenize.INDENT, tokenize.DEDENT,
                                    tokenize.COMMENT, tokenize.ENDMARKER)]
    variables = []
    for index, token in enumerate(tokens):
        if token.type != tokenize.NAME or keyword.iskeyword(token.string):
            continue
        previous = tokens[index - 1].string if index else None
        following = tokens[index + 1].string if index + 1 < len(tokens) else None
        if previous == '.' or following in ('.', '(', '='):
            continue
        if token.string not in variables:
            variables.append(token.string)

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
            "interactions":interactions, 'terms':all_terms,
            'variables': variables}

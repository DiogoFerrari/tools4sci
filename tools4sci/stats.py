
__all__ = ['sig_marks']

def sig_marks(pvalues=None, alpha_levels=None, output='indicators'):
    """
    Converts a vector of p-values to sig_indiator level indicators
    based on given alpha levels.

    Inputs
    ------
        pvalues : list of floats
            A list of p-values. If None, return output='marks'

        alpha_levels: dict
            A dictionary where keys are alpha levels (float) and values
            are the corresponding significance indicators (str).
            Default: {0.001: '***', 0.01: '**', 0.05: '*', 0.1: '+'}

        output : str
           If 'indicators', return a list of significance level
               indicators corresponding to the p-values based on 'alpha_levels'.
           If 'both', return a tuple ('alpha_levels', <indicators>)
           If 'marks', return a string with the map of alpha-levels to
               their marks
           If 'marks_dict', return the dictionary 'alpha_levels'

    Returns
    -------
    See 'output'.
    """
    if alpha_levels is None:
        alpha_levels = {0.1: '+', 0.05: '*', 0.01: '**', 0.001: '***'}
    
    if pvalues is not None:
        alphas = sorted(alpha_levels.keys())
        sig = []
        for p in pvalues:
            sig_indiator = None
            for alpha in alphas:
                if p <= alpha:
                    sig_indiator = alpha_levels[alpha]
                    break
            if sig_indiator is None:
                sig_indiator = ' '
            sig.append(sig_indiator)
    else:
        output='marks'

    if output=='indicators':
        res = sig
    elif output=='both':
        res = (alpha_levels, sig)
    elif output=='marks':
        res = "; ".join([f"{m} $p<{pvalue}$"
                         for pvalue, m in alpha_levels.items()])
    elif output=="marks_dict":
        res = alpha_levels
    
    return res

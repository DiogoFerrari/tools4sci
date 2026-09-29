import pandas as pd
import re
import tidypolars4sci as tp
from .stats import sig_marks
import numpy as np

__all__ = ['models2tab']

def to_latex(tibble, *args, **kws):
    return tibble.to_latex(*args, **kws)

def models2tab(models,
               fit_stats=["N. Obs.",
                          "R2 (adj)",
                          "R2 (pseudo)",
                          "BIC",
                          "AIC",
                          "Std. Error"],
               show_se=True,
               show_ci=False,
               show_stars=True,
               digits=4,
               latex = False,
               kws_latex = None,
               kws_multinomial={},
               covar_labels = None,
               interaction_char = {":":" x "},
               sanitize = True,
               sanitize_option='partial',
               linebreak=True
               ):
    """Create a formatted coefficient summary table for fitted models.

    Parameters
    ----------
    models : list or dict
        Fitted models to include in the table. A list is labeled ``Model 1``,
        ``Model 2``, and so on. When a dictionary is supplied, its keys are
        used as the table's column names.
    fit_stats : list of str, optional
        Summary statistics to append below the coefficient rows, in display
        order. Available values are ``"N. Obs."``, ``"R2 (adj)"``,
        ``"R2 (pseudo)"``, ``"BIC"``, ``"AIC"``, and ``"Std. Error"``.
    show_se : bool, default=True
        Whether to show standard errors in parentheses below coefficients.
    show_ci : bool, default=False
        Whether to show confidence intervals below coefficients. Takes
        precedence over ``show_se`` when both are True.
    show_stars : bool, default=True
        Whether to append significance stars to coefficient estimates.
    linebreak : bool, default=True
        Whether to display estimates and their standard errors or confidence
        intervals on separate rows. If False, display them together in a
        single cell.
    digits : int, default=4
        Number of decimal places used to display estimates and fit statistics.
    latex : bool, default=False
        Whether to return the table as LaTeX rather than a tibble.
    kws_latex : dict, optional
        Keyword arguments passed to the table's ``to_latex`` method. Supplying
        this argument also produces LaTeX output.
    kws_multinomial : dict, default={}
        Options for multinomial models. Set ``"y_labels"`` to outcome labels
        indexed by category number.
    covar_labels : dict, optional
        Regular-expression replacements for coefficient names.
    interaction_char : dict, default={":": " x "}
        Regular-expression replacements for interaction separators in
        coefficient names.
    sanitize : bool, default=True
        Whether to simplify categorical-variable names.
    sanitize_option : str, default="partial"
        If ``"full"``, remove categorical variable names and retain only their
        categories. If ``"partial"``, retain both variable names and categories.

    Returns
    -------
    tidypolars4sci.tibble or str
        The formatted summary table, or its LaTeX representation when
        ``latex`` or ``kws_latex`` is supplied.
    """
    assert isinstance(models, (list, dict)), "'models' must be a list or dictionary of fitted models"
    kws_latex = kws_latex or {}

    # final_columns will be a list of tuples: (column_name, result_dict, model_instance)
    final_columns = []
    # ordered_params will hold the union of parameter names (in order of first appearance)
    ordered_params = []

    if not isinstance(models, dict):
        models = {f"Model {i+1}":m for i, m in enumerate(models)}
        
    for i, (model_name, m) in enumerate(models.items()):
        # model_name = getattr(m, "model_name", f"Model {i+1}")
        res = __models2tab_extract_model_results__(m)
        ci_res = __models2tab_extract_model_confidence_intervals__(m) if show_ci else None
        
        # Check if this model is multinomial (MNLogit)
        if hasattr(m, 'model') and m.model.__class__.__name__ == 'MNLogit':
            # For each outcome level, create a separate column.
            for outcome in m.params.columns:
                if kws_multinomial.get("y_labels", False):
                    try:
                        y_name = kws_multinomial['y_labels'][outcome+2]
                    except:
                        assert False, ("All categories of the outcome "+
                                       "for a multinomial model should "+
                                       "be provided on y_label of "+
                                       "kws_multinomial")
                else:
                    y_name = outcome+2
                col_name = f"{model_name} {y_name}"
                final_columns.append((col_name, res[outcome],
                                      ci_res[outcome] if ci_res is not None else None,
                                      m))
            # Update ordered_params using the parameter names (the rows of m.params)
            for param in m.params.index:
                if param not in ordered_params:
                    ordered_params.append(param)
        else:
            # Non-multinomial model: res is a dict mapping parameter name to (est, se, pvalue)
            col_name = model_name
            final_columns.append((col_name, res, ci_res, m))
            for param in res.keys():
                if param not in ordered_params:
                    ordered_params.append(param)
    
    # Build the coefficient table.
    coef_table = pd.DataFrame(index=ordered_params,
                              columns=[col_name for (col_name, _, _, _) in final_columns])
    se_table = pd.DataFrame(index=ordered_params,
                            columns=[col_name for (col_name, _, _, _) in final_columns])
    ci_table = pd.DataFrame(index=ordered_params,
                            columns=[col_name for (col_name, _, _, _) in final_columns])
    
    for col_name, res, ci_res, m in final_columns:
        for param in ordered_params:
            if param in res:
                est, se, p_val = res[param]
                stars = sig_marks([p_val])[0] if show_stars else ""
                # coef_table.loc[param, col_name] = f"{est:.{digits}f}{stars}\n({se:.{digits}f})"
                coef_table.loc[param, col_name] = f"{est:.{digits}f}{stars}"
                se_table.loc[param, col_name] = f"({se:.{digits}f})"
                if ci_res is not None:
                    lower, upper = ci_res[param]
                    ci_table.loc[param, col_name] = f"({lower:.{digits}f}, {upper:.{digits}f})"
                if not linebreak:
                    if show_ci:
                        coef_table.loc[param, col_name] += f" {ci_table.loc[param, col_name]}"
                    elif show_se:
                        coef_table.loc[param, col_name] += f" {se_table.loc[param, col_name]}"
            else:
                coef_table.loc[param, col_name] = ""
                se_table.loc[param, col_name] = ""
                ci_table.loc[param, col_name] = ""
    # print(coef_table )
    # print(se_table )
    if linebreak and show_ci:
        coef_table = __models2tab_combine_tables__(coef_table, ci_table)
    elif linebreak and show_se:
        coef_table = __models2tab_combine_tables__(coef_table, se_table)

    # Build the summary statistics for each column.
    stats_dict = {}
    for col_name, res, ci_res, m in final_columns:
        # Observations
        n_obs = int(m.nobs) if hasattr(m, "nobs") else ""
        
        # R2 (adjusted) or pseudo R2
        if hasattr(m, "rsquared_adj"):
            r2_adj = m.rsquared_adj
            r2_adj_str = f"{r2_adj:.{digits}f}"
        elif hasattr(m, "prsquared"):
            r2_adj = m.prsquared
            r2_adj_str = f"{r2_adj:.{digits}f}"
        else:
            r2_adj_str = ""
            
        # R2 (pseudo) via method pseudo_rsquared() if available.
        r2_pseudo_str = ""
        if callable(getattr(m, "pseudo_rsquared", None)):
            try:
                r2_pseudo = m.pseudo_rsquared()
                r2_pseudo_str = f"{r2_pseudo:.{digits}f}"
            except Exception:
                r2_pseudo_str = ""
                
        # BIC and AIC
        bic = f"{m.bic:.{digits}f}" if hasattr(m, "bic") else ""
        aic = f"{m.aic:.{digits}f}" if hasattr(m, "aic") else ""
        
        # Determine standard error type.
        if hasattr(m, "cov_type"):
            cov_type = m.cov_type
        else:
            cov_type = "nonrobust"
        if isinstance(cov_type, str):
            cov_type_lower = cov_type.lower()
        else:
            cov_type_lower = str(cov_type).lower()
        if cov_type_lower in ['nonrobust']:
            se_type = "classical"
        elif cov_type_lower.startswith('hc'):
            se_type = "robust"
        elif "cluster" in cov_type_lower:
            se_type = "clustered"
        else:
            se_type = cov_type
        se_type = se_type.title()
        
        col_stats = {
            "N. Obs.": n_obs,
            "R2 (adj)": r2_adj_str,
            "R2 (pseudo)": r2_pseudo_str,
            "BIC": bic,
            "AIC": aic,
            "Std. Error": se_type
        }
        stats_dict[col_name] = col_stats
    
    stats_df = pd.DataFrame(stats_dict)
    # Reorder rows in the stats_df according to fit_stats and drop entirely empty rows.
    stats_df = stats_df.reindex(fit_stats)
    stats_df = stats_df.loc[~(stats_df == "").all(axis=1)]
    
    # Append the summary statistics rows to the coefficient table.
    tab = pd.concat([coef_table, stats_df])
    tab = tab.astype(str)
    tab = tab.reset_index(drop=False, names='Covars')
    tab['Covars'] = tab['Covars'].mask(tab['Covars'] == tab['Covars'].shift(), "")
    tab = tp.from_pandas(tab)

    if sanitize:
        tab = tab.mutate(Covars = tp.map(['Covars'], lambda row:
                                         __models2tab_sanitize_string__(
                                             s=row[0],
                                             option=sanitize_option
                                         )))
    if covar_labels is not None:
        tab = tab.replace({'Covars':covar_labels}, regex=True)
    if interaction_char:
        tab = tab.replace({'Covars':interaction_char}, regex=True)

    res = tab.rename({"Covars":''})
    if latex or kws_latex:
        tabl = __model2tab_to_latex__(res, kws_latex)
        res = tabl

    return res

def __model2tab_to_latex__(res, kws_latex):
    if not kws_latex.get("footnotes", False):
        kws_latex |= {"footnotes" : {'r':[sig_marks()]}}
    else:
        if not kws_latex["footnotes"].get("r", False):
            kws_latex["footnotes"] = {'r':[sig_marks()]}
        else:
            if isinstance(kws_latex["footnotes"]['r'], str):
                kws_latex["footnotes"]['r'] = [kws_latex["footnotes"]['r']]
            kws_latex["footnotes"]['r'] += [sig_marks()]
    tabl = res.to_latex(**kws_latex)
    return tabl

def __models2tab_extract_model_results__(m):
    # Check if this is a multinomial model.
    if hasattr(m, 'model') and m.model.__class__.__name__ == 'MNLogit':
        # In MNLogit, m.params is a DataFrame with index = parameter names
        # and columns = outcome levels (non-reference levels).
        results = {}
        for outcome in m.params.columns:
            results[outcome] = {}
            for param in m.params.index:
                results[outcome][param] = (m.params.loc[param, outcome],
                                             m.bse.loc[param, outcome],
                                             m.pvalues.loc[param, outcome])
        return results
    else:
        # For non-multinomial models:
        if isinstance(m.params, pd.DataFrame):
            # Sometimes models return a DataFrame even if not multinomial.
            # Here we “flatten” the DataFrame so that keys are like "var (label)".
            flat_params = m.params.stack()
            flat_se = m.bse.stack()
            flat_pvals = m.pvalues.stack()
            results = {}
            for (var, label) in flat_params.index:
                param_name = f"{var} ({label})"
                results[param_name] = (flat_params.loc[(var, label)],
                                         flat_se.loc[(var, label)],
                                         flat_pvals.loc[(var, label)])
            return results
        else:
            # Most common case (e.g. OLS, Logit): m.params is a Series.
            return {param: (m.params[param], m.bse[param], m.pvalues[param])
                    for param in m.params.index}

def __models2tab_extract_model_confidence_intervals__(m):
    intervals = np.asarray(m.conf_int())

    if hasattr(m, 'model') and m.model.__class__.__name__ == 'MNLogit':
        n_terms = len(m.params.index)
        n_outcomes = len(m.params.columns)
        intervals = intervals.reshape(n_outcomes, n_terms, 2)
        return {
            outcome: {
                param: tuple(intervals[j, i])
                for i, param in enumerate(m.params.index)
            }
            for j, outcome in enumerate(m.params.columns)
        }

    if isinstance(m.params, pd.DataFrame):
        params = [f"{var} ({label})" for var, label in m.params.stack().index]
    else:
        params = list(m.params.index)
    intervals = intervals.reshape(len(params), 2)
    return {param: tuple(interval) for param, interval in zip(params, intervals)}

def __models2tab_sanitize_string__(s, option):
    # If "[T." is not found, return the original string.
    if "[T." not in s:
        new_s = s
    # This regex finds any substring that starts with zero or more word characters
    # (e.g. "pid" or "ab"), followed immediately by "[T.", then captures everything
    # up to the closing bracket, and then optionally any trailing characters
    # that are not a colon or a word character.
    # The replacement is just the captured group.
    else:
        if option =='full':
            new_s = re.sub(r'\w*\[T\.([^]]+)\][^:\w]*', r'\1', s)
        elif option=='partial':
            new_s = re.sub(r'([^]]+)\[T\.([^]]+)\][^:\w]*', r'\1 (\2)', s)
    return new_s

def __models2tab_combine_tables__(tab1, tab2):
    tab1 = tab1.assign(__order_1__=range(tab1.shape[0]), __order_2__=1)
    tab2 = tab2.assign(__order_1__=range(tab2.shape[0]), __order_2__=2)
    tab1 = pd.concat([tab1, tab2])\
                   .sort_values(['__order_1__', '__order_2__'])\
                   .drop(['__order_1__', '__order_2__'], axis=1)
    return tab1

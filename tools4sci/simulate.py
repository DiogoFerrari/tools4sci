import polars as pl
import tidypolars4sci as tp
import pandas as pd
import numpy as np
import json
from .formulas import extract_variables
from itertools import product
from typing import List, Dict, Optional, Union, Any, Mapping

__all__ = ['newdata']

def data(n: int,
         continuous: Optional[List[str]] = None,
         categorical: Optional[Dict[str, List[str]]] = None,
         binary: Optional[Dict[str, float]] = None,
         formula: Optional[str] = None,
         coefficients: Optional[Union[Dict[str, float], Dict[Any, Dict[str, float]]]] = None,
         family: Optional[str] = None,
         var_e: Optional[float] = None,
         seed: Optional[int] = None,
         ) -> str:
    """Generate a synthetic data set and return it as a JSON string.

    Parameters
    ----------
    n
        Number of rows to generate.
    continuous
        List of names for N(0, 1) predictors.
    categorical
        Mapping ``{var: [cat1, cat2, …]}``; categories are sampled uniformly.
    binary
        Mapping ``{var: p}`` where *p* is the probability of a 1 (Bernoulli).
    formula
        An expression ``<outcome> ~ var1 + var2 + …`` **without numeric coefficients**.
        If omitted, no *outcome* column is added.
    coefficients
        Optional coefficients.  If *None*, they are drawn **randomly** using a
        uniform prior from -1 to 1 (and stored in the returned dict).

        * Gaussian / binomial → ``{var: beta, …}`` (use key ``"Intercept"`` for the constant term).
        * Multinomial        → ``{class_label: {var: beta, …}, …}``.

        For categorical predictors pass keys as ``"var.category"`` (e.g. ``"city.Madrid"``).
    family
        Outcome family: ``"gaussian"`` (default), ``"binomial"``, or ``"multinomial"``.
    var_e
        Standard deviation of the disturbance term (defaults to 1 when needed).
    seed
        Seed for reproducibility.

    Returns
    -------
    tibble or dict
        dict is returned when formula is provided but not the linear coefficients
    """

    rng = np.random.default_rng(seed)

    # 1. Generate predictors
    continuous = continuous or []
    categorical = categorical or {}
    binary = binary or {}

    df: Dict[str, Union[np.ndarray, pd.Series]] = {}

    for name in continuous:
        df[name] = rng.normal(0.0, 1.0, n)

    for name, cats in categorical.items():
        df[name] = rng.choice(cats, size=n)

    for name, p in binary.items():
        df[name] = rng.binomial(1, p, size=n)

    df = pd.DataFrame(df)

    # 2. Optional outcome
    if formula is not None:

        # Random‑draw coefficients if none provided
        if coefficients is None:
            coefficients = _random_coefficients(
                formula=formula,
                categorical=categorical,
                family=family,
                rng=rng,
            )

        family = (family or "gaussian").lower()
        lhs, _ = _data_split_formula(formula)

        if family == "gaussian":
            df[lhs] = _data_gaussian_outcome(df, coefficients, var_e, rng)
        elif family == "binomial":
            df[lhs] = _data_binomial_outcome(df, coefficients, var_e, rng)
        elif family == "multinomial":
            if not isinstance(coefficients, Mapping) or not all(
                isinstance(v, Mapping) for v in coefficients.values()
            ):
                raise ValueError(
                    "For multinomial, 'coefficients' must be a dict-of-dicts: {class_label: {var: beta, …}}"
                )
            df[lhs] = _data_multinomial_outcome(df, coefficients, var_e, rng)
        else:
            raise ValueError("family must be 'gaussian', 'binomial', or 'multinomial'.")

    # 3. Return as tibble with categorical variables, if used
    df = tp.from_pandas(df)
    if categorical:
        for v, cats in categorical.items():
            df = df.mutate(**{v: tp.as_factor(v, cats)})
            
    return {'data':df, 'coefficients': coefficients}

def _random_coefficients(formula: str, categorical: Dict[str, List[str]], family: str, rng):
    """Generate a random coefficient structure compatible with the requested family."""
    # lhs, rhs = _data_split_formula(formula)
    formula_parssed = extract_variables(formula)
    rhs_vars = [v for v in formula_parssed['variables'] if v not in formula_parssed['lhs']]

    def _single_coef_dict() -> Dict[str, float]:
        coef_d: Dict[str, float] = {"Intercept": rng.uniform(-1, 1)}
        for var in rhs_vars:
            if var in categorical:
                for level in categorical[var]:
                    coef_d[f"{var}.{level}"] = rng.uniform(-1, 1)
            else:
                coef_d[var] = rng.uniform(-1, 1)
        return coef_d

    if family == "multinomial":
        classes = [f"Class{i}" for i in range(1, 4)]  # default 3 classes
        return {cls: _single_coef_dict() for cls in classes}
    else:
        return _single_coef_dict()

def _data_split_formula(formula: str) -> tuple[str, str]:
    """Very lightweight split of ``lhs ~ rhs`` into (lhs, rhs) strings."""
    lhs, rhs = map(str.strip, formula.split("~", 1))
    return lhs, rhs

def _data_prepare_noise(n: int, var_e: Optional[float], rng: np.random.Generator) -> np.ndarray:
    """Return a noise vector with SD = var_e or 1 if None."""
    sd = float(var_e or 1.0)
    return rng.normal(0.0, sd, n)

def _data_linear_predictor(df: pd.DataFrame, coefs: Dict[str, float]) -> np.ndarray:
    """Compute the linear predictor ∑ beta_j x_j for each row.

    * Continuous / binary: use the column directly.
    * Categorical: expect keys like "var.level" and create a 0/1 indicator.
    * Intercept: key "Intercept" (added once).
    """
    eta = np.zeros(len(df))

    for key, beta in coefs.items():
        if key == "Intercept":
            eta += beta
            continue

        if "." in key:
            var, level = key.split(".", 1)
            if var not in df.columns:
                raise KeyError(f"Categorical variable '{var}' not found in data frame.")
            eta += beta * (df[var] == level).astype(float)
        else:
            if key not in df.columns:
                raise KeyError(f"Predictor '{key}' not found in data frame.")
            eta += beta * df[key].astype(float)
    return eta

def _data_gaussian_outcome(df: pd.DataFrame, coefs: Dict[str, float], var_e, rng):
    eta = _data_linear_predictor(df, coefs)
    noise = _data_prepare_noise(len(df), var_e, rng)
    return eta + noise

def _data_logit(x):
    return 1.0 / (1.0 + np.exp(-x))

def _data_binomial_outcome(df: pd.DataFrame, coefs: Dict[str, float], var_e, rng):
    eta = _data_linear_predictor(df, coefs)
    p = _data_logit(eta)
    return rng.binomial(1, p)

def _data_multinomial_outcome(df: pd.DataFrame, coef_dict: Dict[Any, Dict[str, float]], var_e, rng):
    classes = list(coef_dict.keys())
    logits = np.column_stack([_data_linear_predictor(df, coef_dict[c]) for c in classes])

    # Soft‑max for probabilities
    logits -= logits.max(axis=1, keepdims=True)  # numerical stability
    probs = np.exp(logits)
    probs /= probs.sum(axis=1, keepdims=True)

    return [rng.choice(classes, p=row) for row in probs]


def newdata(data=None, at={}) -> tp.tibble:
    """
    Creates a synthetic tidyversepy DataFrame.
    Generates all combinations of values provided in 'at', and
    set column to specific values profided in 'fixed'.

    Args:
        data: tp.tibble
           Original data to use as baseline to create the new data.
           If null, create synthetic data from scracth using 'at'
           and 'fixed' only.

        at: dict
           A dictionary with variable names (keys) and 
           the range of values (values) for creating new data.
           Resulting tibble will have all combination of values
           provided in this argument.

        fixed: dict
           A dictionary with variable names (keys) and 
           the range of values (values) for creating new data.
           Resulting tibble will fix the values of the variables
           as defined in this argument

    Returns:
        A synthetic tibble DataFrame.
    """

    if data is not None:
        assert isinstance(data, tp.tibble), "'data' must be a tibble DataFrame"
        newdata = newdata_from_old_data(data, at)
    else:
        newdata = newdata_from_scracth(at=at)
    return newdata

def newdata_from_old_data(data, at):

    data = data.to_polars()
    newdata = {}

    # Generate all combinations of prediction values
    all_combinations = list(product(*at.values()))

    for col in data.columns:
        if col in at:
            newdata[col] = [comb[list(at.keys()).index(col)] for comb in all_combinations]
        # elif col in fixed:
        #     newdata[col] = fixed[col]
        else:
            if data[col].dtype in [pl.Float32, pl.Float64, pl.Int8, pl.Int16, pl.Int32, pl.Int64]:
                # Numerical: use the mean
                newdata[col] = [data[col].mean()] * len(all_combinations)
            else:
                # Non-numerical: use the first value in alphabetical order
                newdata[col] = [sorted(data[col].unique())[0]] * len(all_combinations)

    return tp.tibble(newdata)

def newdata_from_scracth(at):


    newdata = {}

    # Generate all combinations of prediction values
    all_combinations = list(product(*at.values()))

    for col in at:
        newdata[col] = [comb[list(at.keys()).index(col)] for comb in all_combinations]
    # for col in fixed:
    #     newdata[col] = fixed[col]

    return tp.tibble(newdata)

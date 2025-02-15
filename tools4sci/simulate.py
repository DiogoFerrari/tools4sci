from itertools import product
import polars as pl
import tidypolars4sci as tp

__all__ = ['newdata']

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

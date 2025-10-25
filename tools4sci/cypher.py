import tidypolars4sci as tp
import os
import warnings
warnings.filterwarnings("ignore")
# R settings
os.environ['R_PROFILE'] = 'NULL'
os.environ['R_HISTFILE'] = 'NULL'
from rpy2.rinterface_lib.callbacks import logger as rpy2_logger
import logging
rpy2_logger.setLevel(logging.ERROR)   # will display errors, but not warnings
# core
import rpy2.rinterface as ri
import rpy2.robjects as robj
from rpy2.robjects.packages import importr
from rpy2.robjects import pandas2ri, conversion, vectors
from rpy2.robjects.conversion import get_conversion, localconverter
# packages
tibble = importr("tibble")

class convert:

    def __init__(self, *args, **kws):
        pass

    # R -> Python
    # -----------
    def rtibble2tp(self, dfr, rownames2col=None):
        """
        "Convert R tibble to python tidypolars4sci
        rownames2col : string with the name of the column to put
                       rownames information
        """
        if rownames2col is not None:
            dfr = tibble.rownames_to_column(dfr, var=rownames2col)

        with (robj.default_converter + pandas2ri.converter).context():
            dfp = robj.conversion.get_conversion().rpy2py(dfr)

        return tp.from_pandas(dfp)

    def rvec2list(self, v):
        return list(v)

    def rlist2list(self, v):
        return  [list(i) for i in v]

    def rlist2dict(self, x):
        # R NULL
        if x is ri.NULL:
            return None

        # R named/unnamed list
        if isinstance(x, vectors.ListVector):
            names = list(x.names) if x.names is not ri.NULL else None
            items = [convert().rlist2dict(elt) for elt in list(x)]

            # Named -> dict ; Unnamed -> list
            if names and any(n is not None for n in names):
                # If a name is None (can happen), fall back to positional key
                return { (n if n is not None else str(i+1)): v
                         for i, (n, v) in enumerate(zip(names, items)) }
            else:
                return items

        # Atomic vectors (integer, double, logical, character, etc.)
        if isinstance(x, vectors.Vector):
            py_vals = list(x)
            return py_vals[0] if len(py_vals) == 1 else py_vals

        # Fallback: return as-is
        return x

    def rvec2dict(self, v):
        keys = list(v.names)
        values = list(v)
        res = {k:v for k, v in zip(keys, values)}
        return res

    def str(self, obj):
        print(robj.r['capture.output'](robj.r['str'](obj)))
        
    # Python -> R
    # -----------
    def dict2vec(d):
        "Convert Pyton dict to T named vector"
        v = robj.StrVector(d.values())
        v.names = list(d.keys())
        return v

    def dict2list(dict):
        '''
        Convert python dictionary to an R named list of vectors
        '''
        dict_final={}
        for k,v in dict.items():
            if isinstance(v[0], str):
                if isinstance(v, str):
                    v=[v]
                dict_final[k] = robj.StrVector(v)
            else:
                dict_final[k] = robj.FloatVector(v)
        return robj.vectors.ListVector(dict_final)

    def tp2tibble(self, df_tp):
        "Convert tidypolars4sci DataFrame to R tibble"
        df_pandas = df_tp.to_pandas()

        with localconverter(get_conversion() + pandas2ri.converter):
            r_df = conversion.py2rpy(df_pandas)

        return tibble.as_tibble(r_df)

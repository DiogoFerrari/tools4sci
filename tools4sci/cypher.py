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
import rpy2.robjects as robj
from rpy2.robjects.packages import importr
from rpy2.robjects import pandas2ri, conversion
from rpy2.robjects.conversion import get_conversion, localconverter
# packages
tibble = importr("tibble")

class r2py():

    def __init__(self, *args, **kws):
        pass

    def tibble2tp(self, dfr):
        "Convert R tibble to python tidypolars4sci"
        with (robj.default_converter + pandas2ri.converter).context():
            dfp = robj.conversion.get_conversion().rpy2py(dfr)
        return tp.from_pandas(dfp)

    def vec2list(self, v):
        # if :
        return list(v)
        
class py2r():

    def __init__(self, *args, **kws):
        pass
        

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

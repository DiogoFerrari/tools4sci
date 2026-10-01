import os
import re
import altair as alt
from plotnine import ggplot
from typing import Literal
from textwrap import dedent

__all__ = ['save_table',
           'save_figure']

# tables 
# ------
def save_table(fn, tab, tab_latex=None, exts=["xlsx", 'csv', 'tex'],
               kws_latex={}, kws_xlsx={}, kws_csv={"separator":';'},
               caption=None, label=None,
               print_markup: Literal['latex', 'org'] = 'org'):
    """
    Saves a given table in multiple file formats.

    Inputs
    ------
        fn : str, pathlib 
           The filename including path but *wihout extension* to save the table.
           $3^3$

        tab : tibble
           The table to be saved.

        tab_latex:  str, optional. Defaults to None.
            LaTeX table string to be saved if the format is (exts) include 'tex'. 

        exts : list, optional. Defaults to ["xlsx", 'csv', 'tex']
            A list of file extensions to save the table in. 

        kws_latex : dict, optional. Defaults to an empty dictionary.
            Only used if tab_latex is None; otherwise it is ignored.
            Keyword arguments used in the function tibble.to_latex()
            to create the latex table. 

        kws_xlsx : dict. Defaults to an empty dictionary.
            Keywords used in polars write_excel

        kws_csv : dict.
            Defaults to {"separator" : ';'}
            Keywords used in polars write_csv

        caption, label : str, optional.
            Print Org markup that includes the saved LaTeX table and assigns
            it a caption and cross-reference label. Either value may be
            supplied on its own. Missing values are inferred from tab_latex,
            then from the supplied value or filename.

        print_markup : {'latex', 'org'}, optional. Defaults to 'org'.
            Print table markup automatically. Pass False to suppress automatic
            output; providing caption or label still requests markup.
    Returns
    -------
        None
    """
    assert caption is None or isinstance(caption, str), \
        "'caption' must be None or a string"
    assert label is None or isinstance(label, str), \
        "'label' must be None or a string"

    print_markup_requested = bool(print_markup) or \
        caption is not None or label is not None
    label, caption = __infer_table_markup__(
        fn, tab_latex, label=label, caption=caption
    )

    for ext in exts:
        base = os.path.basename(fn)
        print(f'Saving table {base}.{ext}...', end="")

        match ext:
            case 'xlsx':
                tab.to_excel(**{"silently": True, **kws_xlsx, "fn": fn, "ext": "xlsx"})
            case 'csv':
                tab.to_csv(**{"silently": True, **kws_csv, "fn": fn, "ext": "csv"})
            case 'tex':
                __save_table_latex__(fn, tab_latex, kws_latex)
        print('done!')

    if print_markup_requested:
        __save_table_print_org_cmd__(fn, label, caption)

def __save_table_latex__(fn, tab_latex, kws_latex):
    assert tab_latex is not None or kws_latex, """
    Either:
    - Provide the latex table (tab_latex) or
    - Provide the instructions to create the latex table (kws_latex) or
    - Provide extensions (exts) without '.tex'
    """

    if tab_latex is None:
        tab_latex = self.to_latex(**kws_latex)

    with open(f"{fn}.tex", 'w+') as f:
        f.write(tab_latex)

def __infer_table_markup__(fn, tab_latex, label=None, caption=None):
    filename = os.path.basename(fn)

    if tab_latex is not None:
        if label is None:
            match = re.search(r"\\label\s*\{([^}]*)\}", tab_latex)
            if match:
                label = match.group(1)
        if caption is None:
            match = re.search(
                r"\\caption(?:\[[^]]*\])?\s*\{([^}]*)\}", tab_latex
            )
            if match:
                caption = match.group(1)

    label = caption if label is None and caption is not None else label
    label = filename if label is None else label
    caption = label if caption is None else caption
    return label, caption

def __save_table_print_org_cmd__(fn, label, caption):
    filename = os.path.basename(fn)

    s = f"""
    #+Name: {label}
    #+CAPTION: {caption}
    \\input{{./tables-and-figures/{filename}.tex}}
    """
    s = dedent(s.replace("%", "\\%"))
    print(s)

# figures 
# -------
def save_figure(fn, g, tab=None, exts=["pdf", 'eps', 'png'],
                height=None, width=None, png_scale=3,
                caption=None, label=None,
                print_markup: Literal['latex', 'org'] = 'latex',
                latex_env="figure*",
                silently=False
                ):
    assert (caption is None and label is None) |\
        (isinstance(caption, str) and isinstance(label, str)), \
        ("'caption' and 'label' both must "+
         "be None or both a string")
        
    base = os.path.basename(fn)

    for ext in exts:
        if not silently:
            print(f"Saving Figure {base}.{ext}...", end="")
        if ext!='eps':
            scale = png_scale if ext=='png' else 1
            g.save(f'{fn}.{ext}',scale_factor=scale)
        else:
            __save_figure_pdf_to_eps__(fn)      
        if not silently:
            print('done!')

    if tab is not None:
        save_table(fn, tab, exts = ['xlsx', 'csv'])

    if caption and label:
        if print_markup and print_markup=="latex":
            __save_figure_print_latex_cmd__(label, caption, latex_env)
        elif print_markup and print_markup=="org":
            __save_figure_print_org_cmd__(label, caption)

def __save_figure_print_latex_cmd__(label, caption, latex_env):
    s = f"""
    \\begin{{{latex_env}}}[th!]
    \\centering
    \\includegraphics[width=1\\textwidth]{{./tables-and-figures/{label}.pdf}}
    \\caption{{\\label{{{label}}}{caption}}}
    \\end{{{latex_env}}}
    """
    s = dedent(s.replace("%", "\\%"))
    print(s)

def __save_figure_print_org_cmd__(label, caption):
    s = f"""
    #+ATTR_ORG: :width 200/250/300/400/500/600"
    #+ATTR_LATEX: :width 1\\textwidth :placement [ht!] "
    #+Name: {label}
    #+CAPTION: {caption}
    [[./tables-and-figures/{label}.pdf]]
    """
    s = dedent(s.replace("%", "\\%"))
    print(s)

    

def __save_figure_pdf_to_eps__(fn):
    import ghostscript

    fn_pdf = f"{fn}.pdf"
    fn_eps = f"{fn}.eps"

    remove_pdf = False
    if not os.path.isfile(fn_pdf):
        remove_pdf = True
        g.save(fn_pdf)
    
    args = [
        "pdf_to_eps",  # Dummy program name (argument 0)
        "-q",
        "-dNOPAUSE",
        "-dBATCH",
        "-sDEVICE=eps2write",
        f"-sOutputFile={fn_eps}",
        fn_pdf
    ]

    # Call the Ghostscript interpreter with these arguments.
    ghostscript.Ghostscript(*args)

    if remove_pdf:
        os.remove(fn_pdf)

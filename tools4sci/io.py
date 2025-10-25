import os
import altair as alt
from plotnine import ggplot
import ghostscript
from typing import Literal
from textwrap import dedent

__all__ = ['save_table',
           'save_figure']

# tables 
# ------
def save_table(fn, tab, tab_latex=None, exts=["xlsx", 'csv', 'tex'],
               kws_latex={}, kws_xlsx={}, kws_csv={"separator":';'}):
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
    Returns
    -------
        None
    """
    for ext in exts:
        base = os.path.basename(fn)
        print(f'Saving table {base}.{ext}...', end="")

        match ext:
            case 'xlsx':
                tab.to_excel(workbook=f"{fn}.xlsx", **kws_xlsx)
            case 'csv':
                tab.to_csv(file=f"{fn}.csv", **kws_csv)
            case 'tex':
                __save_table_latex__(fn, tab_latex, kws_latex)
        print('done!')

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
    #+Name: {label}
    #+CAPTION: {caption}
    [[./tables-and-figures/{label}.pdf]]
    """
    s = dedent(s.replace("%", "\\%"))
    print(s)

def __save_figure_pdf_to_eps__(fn):

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


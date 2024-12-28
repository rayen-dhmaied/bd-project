import pandas as pd

def season_to_datekey(x):
    """Converts something like '1920/21' to int 192021, or returns None if invalid."""
    if pd.isna(x):
        return None
    x_str = str(x)
    if '/' in x_str:
        parts = x_str.split('/')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return int(parts[0] + parts[1])
    return None


def parse_years(x):
    """Returns (start_year, end_year) from 'YYYY/YY' or (None, None) if invalid."""
    if pd.isna(x):
        return None, None
    x_str = str(x)
    parts = x_str.split('/')
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return int(parts[0]), int(parts[1])
    return None, None
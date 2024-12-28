import streamlit as st
import pandas as pd
from db.db_config import get_connection
from db.create_tables import create_tables
from etl import run_etl


DATA_FILE_PATH = "./data/production_data.xlsx"

@st.cache_data
def load_data(query):
    """Returns a DataFrame from Postgres for the query."""
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def init_db():
    """Initializes DB once per session."""
    if 'initialized_db' not in st.session_state:
        create_tables()
        run_etl(DATA_FILE_PATH)
        st.session_state['initialized_db'] = True

def main():
    init_db()
    st.title("South Africa Crop Dashboard")
    cdf = load_data("SELECT CropKey, CropName FROM dimCrop ORDER BY CropName")
    crops = cdf['cropname'].unique().tolist()
    sel = st.multiselect("Select Crop(s)", crops, default=crops[:1])
    measure_options = {
    "Hectares Planted 🌱": "hectaresplanted",
    "Tons Produced 🚜": "tonsproduced",
    "Yield (Tons per Hectare) 📊": "yieldtonperha"
    }
    measure = st.selectbox(
        "Select a Measure",
        options=list(measure_options.values()),  # Internal values
        format_func=lambda x: next(key for key, value in measure_options.items() if value == x)  # Display names
    )
    if sel:
        in_list = "', '".join(sel)
        sql = f"""
            SELECT fp.*, d.SeasonLabel, d.StartYear, c.CropName
            FROM factProduction fp
            JOIN dimDate d ON fp.DateKey = d.DateKey
            JOIN dimCrop c ON fp.CropKey = c.CropKey
            WHERE c.CropName IN ('{in_list}')
            ORDER BY d.StartYear
        """
        data = load_data(sql)
        if data.empty:
            st.warning("No data found.")
        else:
            pivoted = data.pivot_table(index='seasonlabel', columns='cropname', values=measure, aggfunc='mean')
            st.line_chart(pivoted)
            st.dataframe(data)

if __name__ == "__main__":
    main()

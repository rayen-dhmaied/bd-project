import pandas as pd
from db.db_config import get_connection
from utils.helpers import season_to_datekey, parse_years

def run_etl(excel_file, sheet='data'):
    # 1) Read Excel where row 1 = Commodity Name, row 2 = [Hectare, Ton, Ton/h]
    df = pd.read_excel(excel_file, header=[0,1], sheet_name=sheet)

    # 2) Flatten columns: "CommodityName_Hectare", "CommodityName_Ton", etc.
    df.columns = [
        f"{top.strip()}_{bot.strip()}" for top, bot in df.columns
    ]

    # 3) Rename the first column (if needed) so it’s "Production year"
    #    (Adjust this if your actual column name is different)
    if "Production year_Unnamed: 0_level_1" in df.columns:
        df.rename(columns={"Production year_Unnamed: 0_level_1": "Production year"}, inplace=True)

    # 4) Melt from wide to long
    df_melted = df.melt(
        id_vars=["Production year"],
        var_name="Commodity_Metric",
        value_name="Value"
    )

    # 5) Split "Commodity_Metric" (e.g. "Maize Comm_Hectare") into (CropName, Metric)
    def split_commodity_metric(x):
        parts = x.rsplit("_", 1)  
        commodity = parts[0]
        metric = parts[1] if len(parts) > 1 else "Unknown"
        return pd.Series([commodity, metric])

    df_melted[["CropName","Metric"]] = df_melted["Commodity_Metric"].apply(split_commodity_metric)
    df_melted.drop(columns="Commodity_Metric", inplace=True)

    # 6) Pivot so each row has one CropName and columns for Hectare, Ton, Ton/ha
    df_pivot = df_melted.pivot_table(
        index=["Production year","CropName"],
        columns="Metric",
        values="Value",
        aggfunc="first"
    ).reset_index()

    # Rename pivoted columns if they differ from your original
    # e.g. "Ton/h" might be "Ton/ha" in your data
    df_pivot.columns.name = None
    df_pivot.rename(
        columns={"Ton/h": "Ton/ha"},  # only if needed
        inplace=True
    )

    # 7) Fill NaN with 0
    df_pivot.fillna(0, inplace=True)

    # 8) Parse DateKey, StartYear, EndYear
    df_pivot['DateKey'] = df_pivot['Production year'].apply(season_to_datekey)
    df_pivot['StartYear'], df_pivot['EndYear'] = zip(*df_pivot['Production year'].apply(parse_years))

    # Drop any rows without a valid DateKey
    df_pivot.dropna(subset=['DateKey'], inplace=True)

    # Connect to DB
    conn = get_connection()
    cur = conn.cursor()

    # 9) Insert into dimDate
    ddate = df_pivot[['DateKey','Production year','StartYear','EndYear']].drop_duplicates()
    for _, r in ddate.iterrows():
        cur.execute("""
            INSERT INTO dimDate (DateKey, SeasonLabel, StartYear, EndYear)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (DateKey) DO NOTHING
        """, (
            r['DateKey'],
            r['Production year'],
            r['StartYear'],
            r['EndYear']
        ))

    # 10) Insert into dimCrop, building a CropName -> CropKey map
    dcrop = df_pivot[['CropName']].drop_duplicates()
    crop_map = {}
    for _, r in dcrop.iterrows():
        crop_name = r['CropName']
        cur.execute("""
            INSERT INTO dimCrop (CropName)
            VALUES (%s)
            ON CONFLICT DO NOTHING
            RETURNING CropKey
        """, (crop_name,))
        res = cur.fetchone()
        if res:
            crop_map[crop_name] = res[0]
        else:
            cur.execute("SELECT CropKey FROM dimCrop WHERE CropName = %s", (crop_name,))
            crop_map[crop_name] = cur.fetchone()[0]

    # 11) Insert into factProduction
    #     Ensure you match columns from pivot: e.g. "Hectare","Ton","Ton/ha"
    for _, row in df_pivot.iterrows():
        cur.execute("""
            INSERT INTO factProduction (
                DateKey, CropKey, HectaresPlanted, TonsProduced, YieldTonPerHa
            ) VALUES (%s, %s, %s, %s, %s)
        """, (
            row['DateKey'],
            crop_map[row['CropName']],
            row.get('Hectare', 0),
            row.get('Ton', 0),
            row.get('Ton/ha', 0)
        ))

    conn.commit()
    cur.close()
    conn.close()

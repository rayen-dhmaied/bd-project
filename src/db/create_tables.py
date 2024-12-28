from db.db_config import get_connection

def create_tables():
    """Creates tables if they don't exist."""
    dimDate = """
    CREATE TABLE IF NOT EXISTS dimDate (
        DateKey INT PRIMARY KEY,
        SeasonLabel VARCHAR(10),
        StartYear INT,
        EndYear INT
    );
    """
    dimCrop = """
    CREATE TABLE IF NOT EXISTS dimCrop (
        CropKey SERIAL PRIMARY KEY,
        CropName VARCHAR(50) NOT NULL
    );
    """
    fastProduction = """
    CREATE TABLE IF NOT EXISTS factProduction (
        ProductionID BIGSERIAL PRIMARY KEY,
        DateKey INT NOT NULL REFERENCES dimDate(DateKey),
        CropKey INT NOT NULL REFERENCES dimCrop(CropKey),
        HectaresPlanted DECIMAL(18,2),
        TonsProduced DECIMAL(18,2),
        YieldTonPerHa DECIMAL(18,4)
    );
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(dimDate)
    cur.execute(dimCrop)
    cur.execute(fastProduction)
    conn.commit()
    cur.close()
    conn.close()

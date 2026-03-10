"""
db_setup.py - Heart Disease Analysis
Handles all database operations: creation, loading CSV data into SQLite, and SQL queries.
"""

import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "Heart_new2.csv")
DB_PATH  = os.path.join(BASE_DIR, "data", "heart_disease.db")

def get_engine():
    return create_engine(f"sqlite:///{DB_PATH}")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Load CSV into SQLite and create aggregated views."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    df = pd.read_csv(CSV_PATH)
    df.columns = [c.strip() for c in df.columns]
    engine = get_engine()
    df.to_sql("heart_records", engine, if_exists="replace", index=True, index_label="id")

    with engine.connect() as conn:
        # View: risk factor counts
        conn.execute(text("DROP VIEW IF EXISTS v_risk_counts"))
        conn.execute(text("""
            CREATE VIEW v_risk_counts AS
            SELECT
                SUM(CASE WHEN HeartDisease='Yes' THEN 1 ELSE 0 END)  AS hd_yes,
                SUM(CASE WHEN HeartDisease='No'  THEN 1 ELSE 0 END)  AS hd_no,
                SUM(CASE WHEN Smoking='Yes'       THEN 1 ELSE 0 END)  AS smokers,
                SUM(CASE WHEN AlcoholDrinking='Yes' THEN 1 ELSE 0 END) AS alcohol,
                SUM(CASE WHEN Diabetic='Yes'      THEN 1 ELSE 0 END)  AS diabetic,
                SUM(CASE WHEN PhysicalActivity='Yes' THEN 1 ELSE 0 END) AS active,
                COUNT(*) AS total
            FROM heart_records
        """))

        # View: heart disease by age category
        conn.execute(text("DROP VIEW IF EXISTS v_hd_by_age"))
        conn.execute(text("""
            CREATE VIEW v_hd_by_age AS
            SELECT AgeCategory,
                   SUM(CASE WHEN HeartDisease='Yes' THEN 1 ELSE 0 END) AS hd_count,
                   COUNT(*) AS total
            FROM heart_records
            GROUP BY AgeCategory
        """))

        # View: heart disease by gender
        conn.execute(text("DROP VIEW IF EXISTS v_hd_by_sex"))
        conn.execute(text("""
            CREATE VIEW v_hd_by_sex AS
            SELECT Sex,
                   SUM(CASE WHEN HeartDisease='Yes' THEN 1 ELSE 0 END) AS hd_count,
                   COUNT(*) AS total
            FROM heart_records
            GROUP BY Sex
        """))

        # View: heart disease by general health
        conn.execute(text("DROP VIEW IF EXISTS v_hd_by_genhealth"))
        conn.execute(text("""
            CREATE VIEW v_hd_by_genhealth AS
            SELECT GenHealth,
                   SUM(CASE WHEN HeartDisease='Yes' THEN 1 ELSE 0 END) AS hd_count,
                   COUNT(*) AS total
            FROM heart_records
            GROUP BY GenHealth
        """))

        # View: BMI averages by heart disease
        conn.execute(text("DROP VIEW IF EXISTS v_bmi_avg"))
        conn.execute(text("""
            CREATE VIEW v_bmi_avg AS
            SELECT HeartDisease, ROUND(AVG(BMI),2) AS avg_bmi,
                   ROUND(AVG(SleepTime),2) AS avg_sleep,
                   ROUND(AVG(PhysicalHealth),2) AS avg_phys,
                   ROUND(AVG(MentalHealth),2) AS avg_mental
            FROM heart_records
            GROUP BY HeartDisease
        """))

        conn.commit()

    print(f"[DB] Initialized. Records: {len(df)}  DB: {DB_PATH}")
    return df

def run_query(sql, params=None):
    """Run a raw SQL query and return a DataFrame."""
    engine = get_engine()
    with engine.connect() as conn:
        result = pd.read_sql_query(text(sql), conn, params=params)
    return result

def get_full_df():
    return run_query("SELECT * FROM heart_records")

if __name__ == "__main__":
    init_db()
    print(run_query("SELECT * FROM v_risk_counts"))

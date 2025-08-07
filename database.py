import pandas as pd
import os

FILE_PATH = "transactions.csv"
COLUMNS = ["Date", "Category", "Amount", "Note", "Type"]

def load_data():
    try:
        if os.path.exists(FILE_PATH):
            df = pd.read_csv(FILE_PATH, parse_dates=["Date"])
            if not all(col in df.columns for col in COLUMNS):
                raise ValueError("Missing required columns in CSV")
            return df
    except Exception as e:
        print(f"Error loading data: {e}")
    return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    df.to_csv(FILE_PATH, index=False)

def reset_data():
    df = pd.DataFrame(columns=COLUMNS)
    save_data(df)

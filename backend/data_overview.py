
import pandas as pd


# 1. Get uploaded file name
def get_file_name(uploaded_file):
    return uploaded_file.filename


# 2. Get dataset preview
def get_data_preview(df, rows=5):
    return df.head(rows)


# 3. Get total number of rows
def get_total_rows(df):
    return len(df)


# 4. Get total number of columns
def get_total_columns(df):
    return len(df.columns)


# 5. Get total number of entries
def get_total_entries(df):
    return df.size


# 6. Get total missing values
def get_total_missing_values(df):
    return df.isnull().sum().sum()


# 7. Get total duplicate rows
def get_total_duplicates(df):
    return df.duplicated().sum()


# 8. Get column names
def get_column_names(df):
    return df.columns.tolist()


# 9. Get data types of each column
def get_column_data_types(df):
    return df.dtypes.astype(str).to_dict()

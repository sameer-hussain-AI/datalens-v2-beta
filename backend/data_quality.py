
import pandas as pd


# 1. Calculate overall data completeness percentage
def calculate_completeness(df):
    if df.empty or df.size == 0:
        return 0.0

    total_entries = df.size
    missing_values = df.isnull().sum().sum()

    completeness = ((total_entries - missing_values) / total_entries) * 100

    return round(completeness, 2)


# 2. Calculate overall missing values percentage
def calculate_missing_percentage(df):
    if df.empty or df.size == 0:
        return 0.0

    missing_values = df.isnull().sum().sum()
    total_entries = df.size

    return round((missing_values / total_entries) * 100, 2)


# 3. Get missing values count for each column
def get_missing_values_by_column(df):
    return df.isnull().sum().to_dict()


# 4. Get missing values percentage for each column
def get_missing_percentage_by_column(df):
    if len(df) == 0:
        return {column: 0.0 for column in df.columns}

    missing_percentage = (df.isnull().mean() * 100).round(2)

    return missing_percentage.to_dict()


# 5. Get total missing values
def get_total_missing_values(df):
    return int(df.isnull().sum().sum())


# 6. Get total duplicate rows
def get_total_duplicates(df):
    return int(df.duplicated().sum())


# 7. Calculate duplicate rows percentage
def calculate_duplicate_percentage(df):
    if len(df) == 0:
        return 0.0

    duplicate_count = df.duplicated().sum()

    return round((duplicate_count / len(df)) * 100, 2)


# 8. Get duplicate count for each column
def get_duplicate_values_by_column(df):
    duplicate_counts = {}

    for column in df.columns:
        duplicate_counts[column] = int(
            df[column].duplicated().sum()
        )

    return duplicate_counts


# 9. Get data types of each column
def get_column_data_types(df):
    return df.dtypes.astype(str).to_dict()


# 10. Get columns containing missing values
def get_columns_with_missing_values(df):
    return df.columns[df.isnull().any()].tolist()


# 11. Get columns containing unique values
def get_unique_values_by_column(df):
    return df.nunique(dropna=True).to_dict()


# 12. Get total unique rows
def get_total_unique_rows(df):
    return int(len(df.drop_duplicates()))


# 13. Get a complete data quality summary
def get_data_quality_summary(df):

    return {
        "completeness": calculate_completeness(df),
        "missing_percentage": calculate_missing_percentage(df),
        "total_missing_values": get_total_missing_values(df),
        "total_duplicates": get_total_duplicates(df),
        "duplicate_percentage": calculate_duplicate_percentage(df),
        "total_unique_rows": get_total_unique_rows(df),
        "missing_values_by_column": get_missing_values_by_column(df),
        "missing_percentage_by_column": get_missing_percentage_by_column(df),
        "duplicate_values_by_column": get_duplicate_values_by_column(df),
        "column_data_types": get_column_data_types(df),
        "columns_with_missing_values": get_columns_with_missing_values(df),
        "unique_values_by_column": get_unique_values_by_column(df)
    }

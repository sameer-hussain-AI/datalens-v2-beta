
import pandas as pd
from io import BytesIO


# 1. Remove rows containing missing values
def drop_missing_rows(df, columns=None):
    return df.dropna(subset=columns).copy()


# 2. Remove columns containing missing values
def drop_missing_columns(df):
    return df.dropna(axis=1).copy()


# 3. Fill missing values with a custom value
def fill_missing_with_value(df, value, columns=None):
    cleaned_df = df.copy()

    if columns is None:
        columns = cleaned_df.columns.tolist()

    for column in columns:
        if column not in cleaned_df.columns:
            raise ValueError(f"Column '{column}' does not exist.")

        cleaned_df[column] = cleaned_df[column].fillna(value)

    return cleaned_df


# 4. Fill missing values with mean
def fill_missing_with_mean(df, columns):
    cleaned_df = df.copy()

    for column in columns:
        if column not in cleaned_df.columns:
            raise ValueError(f"Column '{column}' does not exist.")

        if not pd.api.types.is_numeric_dtype(cleaned_df[column]):
            raise ValueError(f"Column '{column}' must be numeric.")

        if cleaned_df[column].notna().any():
            cleaned_df[column] = cleaned_df[column].fillna(
                cleaned_df[column].mean()
            )

    return cleaned_df


# 5. Fill missing values with median
def fill_missing_with_median(df, columns):
    cleaned_df = df.copy()

    for column in columns:
        if column not in cleaned_df.columns:
            raise ValueError(f"Column '{column}' does not exist.")

        if not pd.api.types.is_numeric_dtype(cleaned_df[column]):
            raise ValueError(f"Column '{column}' must be numeric.")

        if cleaned_df[column].notna().any():
            cleaned_df[column] = cleaned_df[column].fillna(
                cleaned_df[column].median()
            )

    return cleaned_df


# 6. Fill missing values with mode
def fill_missing_with_mode(df, columns):
    cleaned_df = df.copy()

    for column in columns:
        if column not in cleaned_df.columns:
            raise ValueError(f"Column '{column}' does not exist.")

        modes = cleaned_df[column].mode(dropna=True)

        if not modes.empty:
            cleaned_df[column] = cleaned_df[column].fillna(modes.iloc[0])

    return cleaned_df


# 7. Remove duplicate rows
def remove_duplicate_rows(df, keep="first"):
    if keep not in ["first", "last", False]:
        raise ValueError("keep must be 'first', 'last', or False.")

    return df.drop_duplicates(keep=keep).copy()


# 8. Remove duplicate values based on selected columns
def remove_duplicate_values(df, columns, keep="first"):
    if not columns:
        raise ValueError("At least one column must be selected.")

    invalid_columns = [col for col in columns if col not in df.columns]

    if invalid_columns:
        raise ValueError(f"Invalid columns: {invalid_columns}")

    return df.drop_duplicates(
        subset=columns,
        keep=keep
    ).copy()


# 9. Rename columns
def rename_columns(df, rename_mapping):
    invalid_columns = [
        col for col in rename_mapping if col not in df.columns
    ]

    if invalid_columns:
        raise ValueError(f"Invalid columns: {invalid_columns}")

    return df.rename(columns=rename_mapping).copy()


# 10. Remove selected columns
def drop_selected_columns(df, columns):
    if not columns:
        raise ValueError("At least one column must be selected.")

    invalid_columns = [col for col in columns if col not in df.columns]

    if invalid_columns:
        raise ValueError(f"Invalid columns: {invalid_columns}")

    return df.drop(columns=columns).copy()


# 11. Change column data types
def change_column_data_type(df, column, data_type):
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist.")

    cleaned_df = df.copy()

    try:
        cleaned_df[column] = cleaned_df[column].astype(data_type)
    except (ValueError, TypeError) as error:
        raise ValueError(
            f"Cannot convert '{column}' to {data_type}: {error}"
        ) from error

    return cleaned_df


# 12. Get cleaning summary
def get_cleaning_summary(original_df, cleaned_df):
    return {
        "original_rows": len(original_df),
        "cleaned_rows": len(cleaned_df),
        "removed_rows": len(original_df) - len(cleaned_df),
        "original_columns": len(original_df.columns),
        "cleaned_columns": len(cleaned_df.columns),
        "removed_columns": len(original_df.columns) - len(cleaned_df.columns),
        "original_missing_values": int(original_df.isnull().sum().sum()),
        "remaining_missing_values": int(cleaned_df.isnull().sum().sum()),
        "original_duplicates": int(original_df.duplicated().sum()),
        "remaining_duplicates": int(cleaned_df.duplicated().sum())
    }


# 13. Export cleaned data as CSV or Excel
def export_cleaned_data(df, file_format="csv"):
    output = BytesIO()

    if file_format.lower() == "csv":
        df.to_csv(output, index=False, encoding="utf-8-sig")

    elif file_format.lower() in ["xlsx", "excel"]:
        df.to_excel(output, index=False, engine="openpyxl")

    else:
        raise ValueError("Supported formats are CSV and Excel.")

    output.seek(0)

    return output

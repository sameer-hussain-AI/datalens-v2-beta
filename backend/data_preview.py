
import pandas as pd


# 1. Get data preview
def get_data_preview(df, rows=5):
    if rows < 0:
        raise ValueError("Rows cannot be negative.")

    return df.head(rows)


# 2. Get selected columns
def get_selected_columns(df, columns=None):
    if columns is None:
        return df.copy()

    invalid_columns = [col for col in columns if col not in df.columns]

    if invalid_columns:
        raise ValueError(f"Invalid columns: {invalid_columns}")

    return df[columns].copy()


# 3. Get custom preview (selected rows and columns)
def get_custom_preview(df, rows=5, columns=None):
    if rows < 0:
        raise ValueError("Rows cannot be negative.")

    selected_data = get_selected_columns(df, columns)
    return selected_data.head(rows)


# 4. Search records across all columns
def search_records(df, search_term):
    if search_term is None or str(search_term) == "":
        return df.iloc[0:0].copy()

    matching_records = df[
        df.astype(str).apply(
            lambda column: column.str.contains(
                str(search_term),
                case=False,
                na=False,
                regex=False
            )
        ).any(axis=1)
    ]

    return matching_records.copy()


# 5. Count search results
def get_search_results_count(df, search_term):
    return len(search_records(df, search_term))


# 6. Pagination
def get_paginated_data(df, page=1, page_size=10):
    if page < 1 or page_size < 1:
        raise ValueError("Page and page size must be positive.")

    start = (page - 1) * page_size
    end = start + page_size

    return df.iloc[start:end].copy()


# 7. Sort data by a selected column
def sort_data(df, column, ascending=True):
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist.")

    return df.sort_values(
        by=column,
        ascending=ascending
    ).copy()


# 8. Filter records by a column value
def filter_data(df, column, value):
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist.")

    return df[df[column] == value].copy()


# 9. Search within a specific column
def search_column(df, column, search_term):
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist.")

    if search_term is None or str(search_term) == "":
        return df.iloc[0:0].copy()

    matching_records = df[
        df[column].astype(str).str.contains(
            str(search_term),
            case=False,
            na=False,
            regex=False
        )
    ]

    return matching_records.copy()


# 10. Reset preview filters
def reset_preview(df):
    return df.copy()


# 11. Get random sample of records
def get_random_sample(df, sample_size=5, random_state=None):
    if sample_size < 1:
        raise ValueError("Sample size must be positive.")

    return df.sample(
        n=min(sample_size, len(df)),
        random_state=random_state
    ).copy()

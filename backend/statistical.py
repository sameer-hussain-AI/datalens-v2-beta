
import pandas as pd
import numpy as np
from scipy import stats


# Helper 1. Validate numeric column
def validate_numeric_column(df, column):

    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist.")

    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"Column '{column}' must be numeric.")


# Helper 2. Get numeric columns
def get_numeric_columns(df):
    return df.select_dtypes(include="number").columns.tolist()


# Helper 3. Get valid numeric data
def get_numeric_data(df, column):

    validate_numeric_column(df, column)

    data = df[column].dropna()

    if data.empty:
        raise ValueError(f"Column '{column}' has no valid numeric values.")

    return data


# 1. Calculate mean
def calculate_mean(df, column):
    return float(get_numeric_data(df, column).mean())


# 2. Calculate median
def calculate_median(df, column):
    return float(get_numeric_data(df, column).median())


# 3. Calculate mode
def calculate_mode(df, column):
    modes = get_numeric_data(df, column).mode()

    return modes.tolist()


# 4. Calculate minimum
def calculate_minimum(df, column):
    return float(get_numeric_data(df, column).min())


# 5. Calculate maximum
def calculate_maximum(df, column):
    return float(get_numeric_data(df, column).max())


# 6. Calculate range
def calculate_range(df, column):
    data = get_numeric_data(df, column)

    return float(data.max() - data.min())


# 7. Calculate variance
def calculate_variance(df, column, ddof=1):
    data = get_numeric_data(df, column)

    if len(data) <= ddof:
        raise ValueError("Not enough values to calculate variance.")

    return float(data.var(ddof=ddof))


# 8. Calculate standard deviation
def calculate_standard_deviation(df, column, ddof=1):
    data = get_numeric_data(df, column)

    if len(data) <= ddof:
        raise ValueError("Not enough values to calculate standard deviation.")

    return float(data.std(ddof=ddof))


# 9. Calculate quartiles
def calculate_quartiles(df, column):
    data = get_numeric_data(df, column)

    quartiles = data.quantile([0.25, 0.50, 0.75])

    return {
        "Q1": float(quartiles.loc[0.25]),
        "Q2": float(quartiles.loc[0.50]),
        "Q3": float(quartiles.loc[0.75])
    }


# 10. Calculate a percentile
def calculate_percentile(df, column, percentile):
    if not 0 <= percentile <= 100:
        raise ValueError("Percentile must be between 0 and 100.")

    return float(
        get_numeric_data(df, column).quantile(percentile / 100)
    )


# 11. Calculate interquartile range
def calculate_iqr(df, column):
    data = get_numeric_data(df, column)

    q1 = data.quantile(0.25)
    q3 = data.quantile(0.75)

    return float(q3 - q1)


# 12. Calculate skewness
def calculate_skewness(df, column):
    data = get_numeric_data(df, column)

    return float(data.skew())


# 13. Calculate kurtosis
def calculate_kurtosis(df, column):
    data = get_numeric_data(df, column)

    return float(data.kurt())


# 14. Calculate correlation between two columns
def calculate_correlation(df, column1, column2, method="pearson"):

    validate_numeric_column(df, column1)
    validate_numeric_column(df, column2)

    if method not in ["pearson", "spearman", "kendall"]:
        raise ValueError("Invalid correlation method.")

    data = df[[column1, column2]].dropna()

    if len(data) < 2:
        raise ValueError("Not enough valid records for correlation.")

    result = data[column1].corr(data[column2], method=method)

    if pd.isna(result):
        return None

    return float(result)


# 15. Calculate covariance between two columns
def calculate_covariance(df, column1, column2):

    validate_numeric_column(df, column1)
    validate_numeric_column(df, column2)

    data = df[[column1, column2]].dropna()

    if len(data) < 2:
        raise ValueError("Not enough valid records for covariance.")

    return float(data[column1].cov(data[column2]))


# 16. Get correlation matrix
def get_correlation_matrix(df, method="pearson"):

    if method not in ["pearson", "spearman", "kendall"]:
        raise ValueError("Invalid correlation method.")

    numeric_data = df.select_dtypes(include="number")

    if numeric_data.shape[1] < 2:
        raise ValueError("At least two numeric columns are required.")

    matrix = numeric_data.corr(method=method)

    return matrix.astype(object).where(
        pd.notna(matrix), None
    ).to_dict()


# 17. Get frequency distribution
def get_frequency_distribution(df, column):

    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist.")

    return df[column].value_counts(dropna=False).to_dict()


# 18. Detect outliers using IQR
def detect_outliers_iqr(df, column):

    data = get_numeric_data(df, column)

    q1 = data.quantile(0.25)
    q3 = data.quantile(0.75)

    iqr = q3 - q1

    lower_bound = q1 - (1.5 * iqr)
    upper_bound = q3 + (1.5 * iqr)

    outlier_mask = (
        (df[column] < lower_bound) |
        (df[column] > upper_bound)
    ).fillna(False)

    outliers = df.loc[outlier_mask].copy()

    return outliers


# 19. Calculate Z-scores
def calculate_z_scores(df, column):

    data = get_numeric_data(df, column)

    if len(data) < 2 or data.std(ddof=0) == 0:
        raise ValueError(
            "At least two values with non-zero variation are required."
        )

    z_scores = pd.Series(
        stats.zscore(data, nan_policy="omit"),
        index=data.index,
        name="z_score"
    )

    return z_scores


# 20. Get descriptive statistics
def get_descriptive_statistics(df, column):

    data = get_numeric_data(df, column)

    return {
        "count": int(data.count()),
        "mean": float(data.mean()),
        "median": float(data.median()),
        "mode": calculate_mode(df, column),
        "minimum": float(data.min()),
        "maximum": float(data.max()),
        "range": calculate_range(df, column),
        "variance": float(data.var()) if len(data) > 1 else None,
        "standard_deviation": (
            float(data.std()) if len(data) > 1 else None
        ),
        "skewness": float(data.skew()) if len(data) > 2 else None,
        "kurtosis": float(data.kurt()) if len(data) > 3 else None,
        "Q1": float(data.quantile(0.25)),
        "Q2": float(data.quantile(0.50)),
        "Q3": float(data.quantile(0.75))
    }

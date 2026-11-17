
import pandas as pd
import matplotlib.pyplot as plt
import textwrap


# =========================================================
# HELPER FUNCTIONS
# =========================================================

# 1. Validate selected columns
def validate_columns(df, columns):

    if not columns or any(column is None for column in columns):
        raise ValueError("Please select the required columns.")

    invalid_columns = [
        col for col in columns if col not in df.columns
    ]

    if invalid_columns:
        raise ValueError(f"Columns not found: {invalid_columns}")


# 2. Validate numeric column
def validate_numeric_column(df, column):

    validate_columns(df, [column])

    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(
            f"Column '{column}' must contain numeric data."
        )


# 3. Create chart figure and axes
def create_chart(figsize=(10, 6)):

    return plt.subplots(figsize=figsize)


# 4. Prepare chart data
def prepare_chart_data(df, x_column, y_column):

    validate_columns(df, [x_column, y_column])
    validate_numeric_column(df, y_column)

    data = df[[x_column, y_column]].copy()

    data[y_column] = pd.to_numeric(
        data[y_column], errors="coerce"
    )

    data = data.replace([float("inf"), float("-inf")], pd.NA)
    data = data.dropna()

    if data.empty:
        raise ValueError(
            "No valid data available for this chart."
        )

    return data


# 5. Shorten long labels
def shorten_labels(labels, max_length=20):

    return [
        str(label)[:max_length] + "..."
        if len(str(label)) > max_length
        else str(label)
        for label in labels
    ]


# =========================================================
# 1. BAR CHART
# =========================================================

def create_bar_chart(
    df, x_column, y_column, title="Bar Chart"
):

    data = prepare_chart_data(
        df, x_column, y_column
    )

    # Limit categories to prevent overcrowding
    if len(data) > 15:
        data = data.nlargest(15, y_column)

    fig, ax = create_chart(figsize=(12, 6))

    labels = shorten_labels(data[x_column])

    ax.bar(labels, data[y_column])

    ax.set_title(title, fontsize=15, pad=15)
    ax.set_xlabel(x_column)
    ax.set_ylabel(y_column)

    ax.tick_params(
        axis="x",
        rotation=35,
        labelsize=9
    )

    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()

    return fig


# =========================================================
# 2. LINE CHART
# =========================================================

def create_line_chart(
    df, x_column, y_column, title="Line Chart"
):

    data = prepare_chart_data(
        df, x_column, y_column
    )

    # Limit very large datasets for rendering performance
    if len(data) > 5000:
        data = data.sample(
            n=5000,
            random_state=42
        ).sort_index()

    fig, ax = create_chart(figsize=(12, 6))

    ax.plot(
        data[x_column].astype(str),
        data[y_column],
        marker="o" if len(data) <= 50 else None,
        linewidth=2
    )

    ax.set_title(title, fontsize=15, pad=15)
    ax.set_xlabel(x_column)
    ax.set_ylabel(y_column)

    if len(data) > 15:
        ax.tick_params(
            axis="x",
            rotation=45,
            labelsize=8
        )

    ax.grid(alpha=0.25)

    fig.tight_layout()

    return fig


# =========================================================
# 3. SCATTER PLOT
# =========================================================

def create_scatter_plot(
    df, x_column, y_column, title="Scatter Plot"
):

    validate_columns(df, [x_column, y_column])

    validate_numeric_column(df, x_column)
    validate_numeric_column(df, y_column)

    data = df[[x_column, y_column]].copy()

    data = data.replace(
        [float("inf"), float("-inf")],
        pd.NA
    ).dropna()

    if data.empty:
        raise ValueError(
            "No valid data available for this chart."
        )

    # Sample large datasets
    if len(data) > 5000:
        data = data.sample(
            n=5000,
            random_state=42
        )

    fig, ax = create_chart(figsize=(10, 6))

    ax.scatter(
        data[x_column],
        data[y_column],
        alpha=0.6
    )

    ax.set_title(title, fontsize=15, pad=15)
    ax.set_xlabel(x_column)
    ax.set_ylabel(y_column)

    ax.grid(alpha=0.25)

    fig.tight_layout()

    return fig


# =========================================================
# 4. HISTOGRAM
# =========================================================

def create_histogram(
    df, column, bins=20, title="Histogram"
):

    validate_numeric_column(df, column)

    if bins < 1:
        raise ValueError(
            "Number of bins must be positive."
        )

    data = pd.to_numeric(
        df[column], errors="coerce"
    )

    data = data.replace(
        [float("inf"), float("-inf")],
        pd.NA
    ).dropna()

    if data.empty:
        raise ValueError(
            "No valid numeric data available."
        )

    fig, ax = create_chart(figsize=(10, 6))

    ax.hist(
        data,
        bins=bins,
        edgecolor="black",
        alpha=0.8
    )

    ax.set_title(title, fontsize=15, pad=15)
    ax.set_xlabel(column)
    ax.set_ylabel("Frequency")

    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()

    return fig


# =========================================================
# 5. PIE CHART
# =========================================================

def create_pie_chart(
    df, column, title="Pie Chart"
):

    validate_columns(df, [column])

    data = df[column].dropna().value_counts()

    if data.empty:
        raise ValueError(
            "No valid data available for this chart."
        )

    # Keep the largest 8 categories
    if len(data) > 8:

        other_count = data.iloc[8:].sum()

        data = data.iloc[:8].copy()

        data.loc["Other"] = other_count

    fig, ax = create_chart(figsize=(9, 7))

    ax.pie(
        data.values,
        labels=data.index.astype(str),
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.75
    )

    ax.set_title(title, fontsize=15, pad=15)

    ax.axis("equal")

    fig.tight_layout()

    return fig


# =========================================================
# 6. BOX PLOT
# =========================================================

def create_box_plot(
    df, column, title="Box Plot"
):

    validate_numeric_column(df, column)

    data = pd.to_numeric(
        df[column], errors="coerce"
    )

    data = data.replace(
        [float("inf"), float("-inf")],
        pd.NA
    ).dropna()

    if data.empty:
        raise ValueError(
            "No valid numeric data available."
        )

    fig, ax = create_chart(figsize=(8, 6))

    ax.boxplot(
        data,
        patch_artist=True,
        showmeans=True
    )

    ax.set_title(title, fontsize=15, pad=15)
    ax.set_ylabel(column)

    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()

    return fig


# =========================================================
# 7. AREA CHART
# =========================================================

def create_area_chart(
    df, x_column, y_column, title="Area Chart"
):

    data = prepare_chart_data(
        df, x_column, y_column
    )

    # Limit very large datasets
    if len(data) > 5000:
        data = data.iloc[:5000]

    fig, ax = create_chart(figsize=(12, 6))

    positions = range(len(data))

    ax.fill_between(
        positions,
        data[y_column],
        alpha=0.3
    )

    ax.plot(
        positions,
        data[y_column],
        linewidth=2
    )

    ax.set_title(title, fontsize=15, pad=15)
    ax.set_xlabel(x_column)
    ax.set_ylabel(y_column)

    if len(data) <= 20:

        ax.set_xticks(list(positions))

        ax.set_xticklabels(
            shorten_labels(data[x_column]),
            rotation=35,
            ha="right"
        )

    else:

        ax.set_xlabel(
            f"{x_column} (row position)"
        )

    ax.grid(alpha=0.25)

    fig.tight_layout()

    return fig


# =========================================================
# 8. HORIZONTAL BAR CHART
# =========================================================

def create_horizontal_bar_chart(
    df,
    x_column,
    y_column,
    title="Horizontal Bar Chart"
):

    data = prepare_chart_data(
        df, x_column, y_column
    )

    # Show the 20 largest values
    if len(data) > 20:
        data = data.nlargest(20, y_column)

    # Sort for easier reading
    data = data.sort_values(y_column)

    fig, ax = create_chart(
        figsize=(12, max(6, len(data) * 0.35))
    )

    ax.barh(
        data[x_column].astype(str),
        data[y_column]
    )

    ax.set_title(title, fontsize=15, pad=15)
    ax.set_xlabel(y_column)
    ax.set_ylabel(x_column)

    ax.grid(axis="x", alpha=0.25)

    fig.tight_layout()

    return fig


# =========================================================
# 9. CORRELATION HEATMAP
# =========================================================

def create_correlation_heatmap(
    df, title="Correlation Heatmap"
):

    # Select actual numeric columns
    numeric_data = df.select_dtypes(
        include="number"
    ).copy()

    # Remove infinite values
    numeric_data = numeric_data.replace(
        [float("inf"), float("-inf")],
        pd.NA
    )

    # Remove columns with insufficient data
    numeric_data = numeric_data.dropna(
        axis=1,
        thresh=2
    )

    # Remove columns with constant values
    numeric_data = numeric_data.loc[
        :,
        numeric_data.nunique(dropna=True) > 1
    ]

    if numeric_data.shape[1] < 2:

        raise ValueError(
            "Correlation heatmap requires at least "
            "two numeric columns with varying values. "
            "Please upload a dataset containing them."
        )

    correlation = numeric_data.corr()

    fig, ax = create_chart(
        figsize=(
            max(9, len(correlation.columns) * 0.8),
            max(7, len(correlation.columns) * 0.7)
        )
    )

    image = ax.imshow(
        correlation,
        cmap="coolwarm",
        vmin=-1,
        vmax=1,
        aspect="auto"
    )

    ax.set_title(
        title,
        fontsize=15,
        pad=20
    )

    ax.set_xticks(
        range(len(correlation.columns))
    )

    ax.set_yticks(
        range(len(correlation.columns))
    )

    ax.set_xticklabels(
        correlation.columns,
        rotation=45,
        ha="right"
    )

    ax.set_yticklabels(
        correlation.columns
    )

    # Display correlation values
    for i in range(len(correlation.columns)):
        for j in range(len(correlation.columns)):

            value = correlation.iloc[i, j]

            if pd.notna(value):

                ax.text(
                    j,
                    i,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=8
                )

    fig.colorbar(
        image,
        ax=ax,
        label="Correlation"
    )

    fig.tight_layout()

    return fig

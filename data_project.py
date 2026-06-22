"""
Retail Sales Analytics Project
Author: Ahmed Alkohly
Role: Junior Python Backend & Data Engineer

Professional version of the original Data Science Mini Project.

This project performs:
- Data loading
- Data cleaning
- Feature engineering
- Sales KPI analysis
- Category and city revenue analysis
- RFM customer segmentation
- Dashboard visualization
- CSV report exporting
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


AUTHOR = "Ahmed Alkohly"
ROLE = "Junior Python Backend & Data Engineer"
SNAPSHOT_DATE = pd.Timestamp("2024-12-31")


def find_sales_file() -> Path:
    """
    Find sales.csv either in the same folder or inside data/sales.csv.
    """
    possible_paths = [
        Path("sales.csv"),
        Path("data") / "sales.csv",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    raise FileNotFoundError(
        "sales.csv not found. Put sales.csv beside this file or inside a data folder."
    )


def create_folders() -> tuple[Path, Path]:
    """
    Create output folders for charts and reports.
    """
    outputs_dir = Path("outputs")
    reports_dir = Path("reports")

    outputs_dir.mkdir(exist_ok=True)
    reports_dir.mkdir(exist_ok=True)

    return outputs_dir, reports_dir


def load_data(file_path: Path) -> pd.DataFrame:
    """
    Load sales dataset.
    """
    sales_df = pd.read_csv(file_path, parse_dates=["date"])
    return sales_df


def clean_data(sales_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the sales dataset.

    Original cleaning logic:
    - Remove duplicates
    - Fill missing city values with Unknown
    - Standardize city names
    - Remove negative quantities
    - Fill missing unit_price using category median
    """
    clean_df = sales_df.drop_duplicates().copy()

    clean_df["city"] = clean_df["city"].fillna("Unknown").str.strip().str.title()

    clean_df = clean_df[clean_df["quantity"] >= 0].copy()

    clean_df["unit_price"] = clean_df["unit_price"].fillna(
        clean_df.groupby("category")["unit_price"].transform("median")
    )

    return clean_df


def add_features(sales_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add revenue, month, and weekday columns.
    """
    sales_df = sales_df.copy()

    sales_df["revenue"] = sales_df["quantity"] * sales_df["unit_price"]
    sales_df["month"] = sales_df["date"].dt.month_name()
    sales_df["weekday"] = sales_df["date"].dt.day_name()

    return sales_df


def calculate_sales_metrics(sales_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Calculate main sales KPIs.
    """
    orders_val = sales_df.groupby("order_id")["revenue"].sum()

    summary = pd.DataFrame([
        {
            "author": AUTHOR,
            "total_revenue": round(sales_df["revenue"].sum(), 2),
            "orders": sales_df["order_id"].nunique(),
            "customers": sales_df["customer_id"].nunique(),
            "categories": sales_df["category"].nunique(),
            "average_order_value": round(orders_val.mean(), 2),
            "median_order_value": round(orders_val.median(), 2),
            "top_category_by_quantity": sales_df.groupby("category")["quantity"].sum().idxmax(),
            "top_category_by_revenue": sales_df.groupby("category")["revenue"].sum().idxmax(),
        }
    ])

    return summary, orders_val


def calculate_revenue_share(sales_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculate revenue share by category and city.
    """
    total_revenue = sales_df["revenue"].sum()

    category_share = (
        sales_df.groupby("category")["revenue"]
        .sum()
        .div(total_revenue)
        .mul(100)
        .round(1)
        .reset_index(name="revenue_share_percent")
        .sort_values("revenue_share_percent", ascending=False)
    )

    city_share = (
        sales_df.groupby("city")["revenue"]
        .sum()
        .div(total_revenue)
        .mul(100)
        .round(1)
        .reset_index(name="revenue_share_percent")
        .sort_values("revenue_share_percent", ascending=False)
    )

    return category_share, city_share


def build_rfm(sales_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build RFM customer segmentation table.

    R = Recency
    F = Frequency
    M = Monetary value
    """
    rfm = sales_df.groupby("customer_id").agg(
        last=("date", "max"),
        F=("order_id", "count"),
        M=("revenue", "sum"),
    )

    rfm["R"] = (SNAPSHOT_DATE - rfm["last"]).dt.days

    rfm["R_score"] = pd.qcut(
        rfm["R"].rank(method="first"),
        4,
        labels=[4, 3, 2, 1]
    ).astype(int)

    rfm["F_score"] = pd.qcut(
        rfm["F"].rank(method="first"),
        4,
        labels=[1, 2, 3, 4]
    ).astype(int)

    rfm["M_score"] = pd.qcut(
        rfm["M"].rank(method="first"),
        4,
        labels=[1, 2, 3, 4]
    ).astype(int)

    rfm["RFM_score"] = rfm[["R_score", "F_score", "M_score"]].sum(axis=1)

    return rfm.sort_values("RFM_score", ascending=False)


def export_reports(
    reports_dir: Path,
    summary: pd.DataFrame,
    category_share: pd.DataFrame,
    city_share: pd.DataFrame,
    rfm: pd.DataFrame,
) -> None:
    """
    Export analysis results to CSV files.
    """
    vip_customers = rfm.sort_values("RFM_score", ascending=False).head()
    churn_risk = rfm.sort_values("RFM_score").head()

    summary.to_csv(reports_dir / "summary_metrics.csv", index=False)
    category_share.to_csv(reports_dir / "category_share.csv", index=False)
    city_share.to_csv(reports_dir / "city_share.csv", index=False)
    rfm.to_csv(reports_dir / "rfm_customers.csv")
    vip_customers.to_csv(reports_dir / "vip_customers.csv")
    churn_risk.to_csv(reports_dir / "churn_risk_customers.csv")


def create_visualizations(
    outputs_dir: Path,
    sales_df: pd.DataFrame,
    rfm: pd.DataFrame,
    orders_val: pd.Series,
) -> None:
    """
    Create RFM scatter plot and sales dashboard.
    """

    # RFM Scatter
    plt.figure(figsize=(8, 6))
    plt.scatter(
        rfm["R"],
        rfm["M"],
        s=rfm["F"] * 25,
        alpha=0.6,
        color="darkred"
    )
    plt.xlabel("Recency")
    plt.ylabel("Revenue")
    plt.title("RFM Scatter")
    plt.tight_layout()
    plt.savefig(outputs_dir / "rfm_scatter_ahmed.png", dpi=120)
    plt.show()

    # Dashboard
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Sales Analytics - 2024")

    sales_df.groupby("category")["revenue"].sum().plot(
        kind="bar",
        ax=axs[0, 0],
        color="gold"
    )
    axs[0, 0].set_title("Revenue by Category")
    axs[0, 0].set_xlabel("Category")
    axs[0, 0].set_ylabel("Revenue")

    sales_df.groupby("city")["revenue"].sum().sort_values().plot(
        kind="barh",
        ax=axs[0, 1],
        color="forestgreen"
    )
    axs[0, 1].set_title("Revenue by City")
    axs[0, 1].set_xlabel("Revenue")
    axs[0, 1].set_ylabel("City")

    axs[1, 0].scatter(
        rfm["R"],
        rfm["M"],
        s=rfm["F"] * 25,
        alpha=0.6,
        color="royalblue"
    )
    axs[1, 0].set_title("RFM Scatter")
    axs[1, 0].set_xlabel("Recency")
    axs[1, 0].set_ylabel("Revenue")

    orders_val.hist(
        bins=20,
        ax=axs[1, 1],
        color="darkorange",
        alpha=0.7
    )
    axs[1, 1].axvline(
        orders_val.median(),
        color="black",
        linestyle="--",
        label="Median"
    )
    axs[1, 1].set_title("Order Value Distribution")
    axs[1, 1].set_xlabel("Order Value")
    axs[1, 1].set_ylabel("Frequency")
    axs[1, 1].legend()

    fig.tight_layout()
    plt.savefig(outputs_dir / "final_dashboard_ahmed.png", dpi=150)
    plt.show()


def print_results(
    summary: pd.DataFrame,
    category_share: pd.DataFrame,
    city_share: pd.DataFrame,
    rfm: pd.DataFrame,
) -> None:
    """
    Print clean terminal output.
    """
    row = summary.iloc[0]

    print("=" * 60)
    print("Retail Sales Analytics Project")
    print(f"Author: {AUTHOR}")
    print(f"Role: {ROLE}")
    print("=" * 60)

    print("Revenue:", row["total_revenue"])
    print("Orders:", row["orders"])
    print("Customers:", row["customers"])
    print("Categories:", row["categories"])
    print("Average order:", row["average_order_value"])
    print("Median order:", row["median_order_value"])

    print("\nCategory share:")
    print(category_share)

    print("\nCity share:")
    print(city_share)

    print("\nTop category by qty:", row["top_category_by_quantity"])
    print("Top category by rev:", row["top_category_by_revenue"])

    print("\nVIPs:")
    print(rfm.sort_values("RFM_score", ascending=False).head())

    print("\nChurn risk:")
    print(rfm.sort_values("RFM_score").head())


def main() -> None:
    """
    Run the full project.
    """
    outputs_dir, reports_dir = create_folders()

    sales_file = find_sales_file()

    sales_df = load_data(sales_file)
    sales_df = clean_data(sales_df)
    sales_df = add_features(sales_df)

    summary, orders_val = calculate_sales_metrics(sales_df)
    category_share, city_share = calculate_revenue_share(sales_df)
    rfm = build_rfm(sales_df)

    export_reports(
        reports_dir=reports_dir,
        summary=summary,
        category_share=category_share,
        city_share=city_share,
        rfm=rfm,
    )

    create_visualizations(
        outputs_dir=outputs_dir,
        sales_df=sales_df,
        rfm=rfm,
        orders_val=orders_val,
    )

    print_results(
        summary=summary,
        category_share=category_share,
        city_share=city_share,
        rfm=rfm,
    )

    print("\nProject completed successfully.")
    print(f"Charts saved in: {outputs_dir}")
    print(f"Reports saved in: {reports_dir}")


if __name__ == "__main__":
    main()
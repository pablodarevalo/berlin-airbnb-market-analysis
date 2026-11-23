"""
Berlin Airbnb Market Analysis — End-to-End ETL & BI Export Pipeline
--------------------------------------------------------------------
1. Cleans raw Inside Airbnb snapshot datasets (`listings-2.csv` and `neighbourhoods.csv`).
2. Standardizes prices, dates, boolean flags, and German character collisions (`ß` -> `ss`).
3. Flags extreme price outliers (> 99th percentile) without dropping records.
4. Loads cleaned relational tables into MySQL (`airbnb_berlin`).
5. Builds the analytical BI view (`vw_airbnb_berlin_bi`) with engineered business tiers
   and exports `airbnb_berlin_tableau.csv` for Tableau Public.
"""

from getpass import getpass
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def clean_raw_datasets(
    listings_path: str = "listings-2.csv",
    neighbourhoods_path: str = "neighbourhoods.csv",
) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """Load, clean, and standardize raw listings and neighbourhoods CSV files."""
    listings_df = pd.read_csv(listings_path, low_memory=False)
    neighbourhoods_df = pd.read_csv(neighbourhoods_path)

    selected_columns = [
        "id",
        "name",
        "last_scraped",
        "neighbourhood_cleansed",
        "latitude",
        "longitude",
        "room_type",
        "accommodates",
        "bedrooms",
        "beds",
        "price",
        "minimum_nights",
        "availability_365",
        "number_of_reviews",
        "review_scores_rating",
        "reviews_per_month",
        "host_id",
        "host_is_superhost",
        "calculated_host_listings_count",
    ]
    clean_df = listings_df[selected_columns].copy()

    # Format snapshot date
    clean_df["last_scraped"] = pd.to_datetime(
        clean_df["last_scraped"], errors="coerce"
    ).dt.date

    # Strip currency symbols/commas and convert price to numeric float
    clean_df["nightly_price"] = pd.to_numeric(
        clean_df["price"]
        .astype(str)
        .str.replace(r"[^0-9.]", "", regex=True)
        .replace("", pd.NA),
        errors="coerce",
    )
    clean_df = clean_df.drop(columns=["price"])

    # Map superhost flag ('t'/'f' -> 1/0)
    clean_df["is_superhost"] = clean_df["host_is_superhost"].map({"t": 1, "f": 0})
    clean_df = clean_df.drop(columns=["host_is_superhost"])

    # Trim whitespace in text columns
    for col in ["name", "neighbourhood_cleansed", "room_type"]:
        clean_df[col] = clean_df[col].astype(str).str.strip()
        clean_df.loc[clean_df[col] == "nan", col] = pd.NA

    # Convert minimum_nights to nullable integer
    clean_df["minimum_nights"] = (
        pd.to_numeric(clean_df["minimum_nights"], errors="coerce").round().astype("Int64")
    )

    # Flag extreme price outliers (> 99th percentile) while preserving full dataset
    p99_price = float(clean_df["nightly_price"].quantile(0.99))
    clean_df["is_high_price_outlier"] = (clean_df["nightly_price"] > p99_price).astype(int)

    final_columns = [
        "id",
        "name",
        "last_scraped",
        "neighbourhood_cleansed",
        "latitude",
        "longitude",
        "room_type",
        "accommodates",
        "bedrooms",
        "beds",
        "nightly_price",
        "is_high_price_outlier",
        "minimum_nights",
        "availability_365",
        "number_of_reviews",
        "review_scores_rating",
        "reviews_per_month",
        "host_id",
        "is_superhost",
        "calculated_host_listings_count",
    ]
    clean_df = clean_df[final_columns]

    # Deduplicate neighbourhoods handling MySQL case-insensitive collation ('ß' -> 'ss')
    clean_neigh_df = neighbourhoods_df.copy()
    clean_neigh_df["neighbourhood_group"] = (
        clean_neigh_df["neighbourhood_group"].astype(str).str.strip()
    )
    clean_neigh_df["neighbourhood"] = (
        clean_neigh_df["neighbourhood"].astype(str).str.strip()
    )
    clean_neigh_df["_norm_key"] = (
        clean_neigh_df["neighbourhood"]
        .str.casefold()
        .str.replace("ß", "ss", regex=False)
    )
    clean_neigh_df = (
        clean_neigh_df.drop_duplicates(subset=["_norm_key"], keep="first")
        .drop(columns=["_norm_key"])
        .copy()
    )

    return clean_df, clean_neigh_df, p99_price


def load_to_mysql(
    engine: Engine,
    listings_df: pd.DataFrame,
    neighbourhoods_df: pd.DataFrame,
) -> None:
    """Load cleaned DataFrames into MySQL relational tables."""
    # Convert NaN/NaT to native Python None for pymysql compatibility
    neigh_py = neighbourhoods_df.astype(object).where(pd.notna(neighbourhoods_df), None)
    listings_py = listings_df.astype(object).where(pd.notna(listings_df), None)

    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        conn.execute(text("TRUNCATE TABLE listings;"))
        conn.execute(text("TRUNCATE TABLE neighbourhoods;"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

        # Insert parent dimension table
        raw_conn = conn.connection
        with raw_conn.cursor() as cur:
            insert_sql = """
                INSERT IGNORE INTO neighbourhoods (neighbourhood_group, neighbourhood)
                VALUES (%s, %s)
            """
            rows = [
                (r["neighbourhood_group"], r["neighbourhood"])
                for r in neigh_py.to_dict(orient="records")
            ]
            cur.executemany(insert_sql, rows)

        # Insert fact table in chunks
        listings_py.to_sql(
            "listings",
            con=conn,
            if_exists="append",
            index=False,
            chunksize=500,
        )

        n_rows = conn.execute(text("SELECT COUNT(*) FROM neighbourhoods")).scalar()
        l_rows = conn.execute(text("SELECT COUNT(*) FROM listings")).scalar()
        p_rows = conn.execute(
            text("SELECT COUNT(*) FROM listings WHERE nightly_price IS NOT NULL")
        ).scalar()

    print(f"MySQL Load Complete -> neighbourhoods: {n_rows} | listings: {l_rows} (valid price: {p_rows})")


def build_bi_view_and_export(
    engine: Engine,
    output_csv: str = "airbnb_berlin_tableau.csv",
) -> None:
    """Create analytical SQL view with business tiers and export flat dataset for Tableau."""
    create_view_sql = """
    CREATE OR REPLACE VIEW vw_airbnb_berlin_bi AS
    SELECT
        l.id,
        l.name,
        l.last_scraped,
        n.neighbourhood_group,
        l.neighbourhood_cleansed AS neighbourhood,
        l.latitude,
        l.longitude,
        l.room_type,
        l.accommodates,
        l.bedrooms,
        l.beds,
        l.nightly_price,
        l.is_high_price_outlier,
        l.minimum_nights,
        CASE
            WHEN l.minimum_nights <= 3 THEN '1-3 nights (Short getaway)'
            WHEN l.minimum_nights BETWEEN 4 AND 14 THEN '4-14 nights (Medium stay)'
            WHEN l.minimum_nights BETWEEN 15 AND 89 THEN '15-89 nights (Extended stay)'
            ELSE '90+ nights (Long-term stay)'
        END AS stay_tier,
        l.availability_365,
        l.number_of_reviews,
        l.review_scores_rating,
        l.reviews_per_month,
        l.host_id,
        CASE WHEN l.is_superhost = 1 THEN 'Superhost' ELSE 'Standard Host' END AS host_status,
        l.calculated_host_listings_count,
        CASE
            WHEN l.calculated_host_listings_count = 1 THEN '1 listing (Single host)'
            WHEN l.calculated_host_listings_count BETWEEN 2 AND 5 THEN '2-5 listings (Small operator)'
            ELSE '6+ listings (Large/Multi operator)'
        END AS host_scale_tier
    FROM listings l
    LEFT JOIN neighbourhoods n
        ON l.neighbourhood_cleansed = n.neighbourhood;
    """

    with engine.begin() as conn:
        conn.execute(text(create_view_sql))

    df_bi = pd.read_sql("SELECT * FROM vw_airbnb_berlin_bi", con=engine)
    df_bi.to_csv(output_csv, index=False)
    print(f"Exported BI dataset -> {output_csv} ({len(df_bi)} rows)")


def main() -> None:
    clean_listings_df, clean_neigh_df, p99 = clean_raw_datasets()
    print(f"Cleaned datasets -> listings: {clean_listings_df.shape} | 99th pct price: {p99:.2f} EUR")

    # Export intermediate clean CSVs
    clean_listings_df.to_csv("berlin_listings_clean.csv", index=False)
    clean_neigh_df.to_csv("berlin_neighbourhoods_clean.csv", index=False)

    # Connect to local MySQL instance and run database load + BI export
    db_password = getpass("Enter MySQL root password: ")
    engine = create_engine(f"mysql+pymysql://root:{db_password}@127.0.0.1:3306/airbnb_berlin")

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    load_to_mysql(engine, clean_listings_df, clean_neigh_df)
    build_bi_view_and_export(engine)


if __name__ == "__main__":
    main()

-- ============================================================================
-- Berlin Airbnb Market Analysis — Exploratory & Analytical SQL Queries
-- Database: airbnb_berlin
-- ============================================================================

USE airbnb_berlin;

-- 1. Dataset coverage, price completeness, and impact of p99 price outliers
SELECT
    COUNT(*) AS total_listings,
    COUNT(nightly_price) AS listings_with_price,
    ROUND(COUNT(nightly_price) * 100.0 / COUNT(*), 2) AS pct_with_price,
    ROUND(AVG(nightly_price), 2) AS avg_price_all,
    ROUND(AVG(CASE WHEN is_high_price_outlier = 0 THEN nightly_price END), 2) AS avg_price_excl_p99_outliers,
    MAX(nightly_price) AS max_price
FROM listings;

-- 2. Snapshot date range and overall nightly price bounds (valid prices)
SELECT
    MIN(last_scraped) AS earliest_scrape,
    MAX(last_scraped) AS latest_scrape,
    MIN(nightly_price) AS min_nightly_price,
    ROUND(AVG(nightly_price), 2) AS avg_nightly_price,
    MAX(nightly_price) AS max_nightly_price
FROM listings
WHERE nightly_price IS NOT NULL;

-- 3. Supply share, average nightly price, and capacity by room type
SELECT
    room_type,
    COUNT(*) AS total_listings,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS supply_share_pct,
    ROUND(AVG(nightly_price), 2) AS avg_nightly_price,
    ROUND(AVG(accommodates), 1) AS avg_accommodates
FROM listings
WHERE nightly_price IS NOT NULL
GROUP BY room_type
ORDER BY total_listings DESC;

-- 4. Top 15 neighbourhoods by average nightly price (excluding p99 outliers)
SELECT
    n.neighbourhood_group,
    l.neighbourhood_cleansed AS neighbourhood,
    COUNT(*) AS priced_listings,
    ROUND(AVG(l.nightly_price), 2) AS avg_nightly_price,
    DENSE_RANK() OVER (ORDER BY AVG(l.nightly_price) DESC) AS price_rank_berlin
FROM listings l
LEFT JOIN neighbourhoods n
    ON l.neighbourhood_cleansed = n.neighbourhood
WHERE l.nightly_price IS NOT NULL
  AND l.is_high_price_outlier = 0
GROUP BY n.neighbourhood_group, l.neighbourhood_cleansed
HAVING COUNT(*) >= 10
ORDER BY price_rank_berlin ASC, priced_listings DESC
LIMIT 15;

-- 5. Neighbourhood price spread relative to its parent district (neighbourhood_group)
SELECT
    n.neighbourhood_group,
    l.neighbourhood_cleansed AS neighbourhood,
    COUNT(*) AS priced_listings,
    ROUND(AVG(l.nightly_price), 2) AS avg_price,
    ROUND(AVG(AVG(l.nightly_price)) OVER (PARTITION BY n.neighbourhood_group), 2) AS group_avg_price,
    ROUND(
        AVG(l.nightly_price) - AVG(AVG(l.nightly_price)) OVER (PARTITION BY n.neighbourhood_group),
        2
    ) AS diff_vs_group_avg
FROM listings l
LEFT JOIN neighbourhoods n
    ON l.neighbourhood_cleansed = n.neighbourhood
WHERE l.nightly_price IS NOT NULL
  AND l.is_high_price_outlier = 0
GROUP BY n.neighbourhood_group, l.neighbourhood_cleansed
HAVING COUNT(*) >= 10
ORDER BY diff_vs_group_avg DESC
LIMIT 15;

-- 6. District-level overview: price, annual availability, rating, and Superhost share
SELECT
    n.neighbourhood_group,
    COUNT(*) AS total_listings,
    COUNT(l.nightly_price) AS priced_listings,
    ROUND(AVG(l.nightly_price), 2) AS avg_price_excl_p99,
    ROUND(AVG(l.availability_365), 1) AS avg_availability_365,
    ROUND(AVG(l.review_scores_rating), 2) AS avg_rating,
    ROUND(AVG(CASE WHEN l.is_superhost = 1 THEN 100.0 ELSE 0.0 END), 1) AS pct_superhost
FROM listings l
LEFT JOIN neighbourhoods n
    ON l.neighbourhood_cleansed = n.neighbourhood
WHERE l.is_high_price_outlier = 0
GROUP BY n.neighbourhood_group
HAVING COUNT(*) >= 20
ORDER BY avg_price_excl_p99 DESC;

-- 7. Stay duration tiers (minimum_nights) vs. nightly price and annual availability
SELECT
    CASE
        WHEN minimum_nights <= 3 THEN '1-3 nights (Short getaway)'
        WHEN minimum_nights BETWEEN 4 AND 14 THEN '4-14 nights (Medium stay)'
        WHEN minimum_nights BETWEEN 15 AND 89 THEN '15-89 nights (Extended stay)'
        ELSE '90+ nights (Long-term stay)'
    END AS stay_tier,
    COUNT(*) AS total_listings,
    COUNT(nightly_price) AS priced_listings,
    ROUND(AVG(nightly_price), 2) AS avg_price_excl_p99,
    ROUND(AVG(availability_365), 1) AS avg_availability_365
FROM listings
WHERE is_high_price_outlier = 0
GROUP BY stay_tier
ORDER BY total_listings DESC;

-- 8. Superhost vs. Standard Host comparison: price, rating, and review volume
SELECT
    CASE
        WHEN is_superhost = 1 THEN 'Superhost'
        ELSE 'Standard Host'
    END AS host_status,
    COUNT(*) AS total_listings,
    ROUND(AVG(nightly_price), 2) AS avg_price_excl_p99,
    ROUND(AVG(review_scores_rating), 2) AS avg_rating,
    ROUND(AVG(number_of_reviews), 1) AS avg_total_reviews,
    ROUND(AVG(reviews_per_month), 2) AS avg_reviews_per_month
FROM listings
WHERE is_high_price_outlier = 0
GROUP BY host_status
ORDER BY total_listings DESC;

-- 9. Host scale tiers and commercial operator (6+ listings) concentration by district
SELECT
    CASE
        WHEN calculated_host_listings_count = 1 THEN '1 listing (Single host)'
        WHEN calculated_host_listings_count BETWEEN 2 AND 5 THEN '2-5 listings (Small operator)'
        ELSE '6+ listings (Large/Multi operator)'
    END AS host_scale_tier,
    COUNT(*) AS total_listings,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS share_pct,
    ROUND(AVG(nightly_price), 2) AS avg_nightly_price,
    ROUND(AVG(availability_365), 1) AS avg_availability_365
FROM listings
WHERE nightly_price IS NOT NULL
  AND is_high_price_outlier = 0
GROUP BY host_scale_tier
ORDER BY total_listings DESC;

-- Bonus / District concentration of multi-listing operators (6+ listings)
SELECT
    n.neighbourhood_group,
    COUNT(*) AS total_listings_excl_p99,
    SUM(CASE WHEN l.calculated_host_listings_count >= 6 THEN 1 ELSE 0 END) AS multi_operator_listings,
    ROUND(
        SUM(CASE WHEN l.calculated_host_listings_count >= 6 THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    ) AS pct_multi_operator,
    RANK() OVER (
        ORDER BY SUM(CASE WHEN l.calculated_host_listings_count >= 6 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) DESC
    ) AS multi_operator_rank
FROM listings l
LEFT JOIN neighbourhoods n
    ON l.neighbourhood_cleansed = n.neighbourhood
WHERE l.is_high_price_outlier = 0
GROUP BY n.neighbourhood_group
HAVING COUNT(*) >= 20
ORDER BY multi_operator_rank ASC;

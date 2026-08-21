-- 1. Highest-value conversations for each relationship manager.
WITH ranked AS (
    SELECT
        rm_id,
        customer_id,
        product_label,
        opportunity_score,
        expected_incremental_profit_try,
        reason_1,
        ROW_NUMBER() OVER (PARTITION BY rm_id ORDER BY opportunity_score DESC) AS rm_rank
    FROM aurelia_sme_sales.next_best_conversation
    WHERE capacity_allocated_flag
)
SELECT * FROM ranked WHERE rm_rank <= 10 ORDER BY rm_id, rm_rank;

-- 2. Relationship-depth gaps by SME segment.
SELECT
    size_band,
    COUNT(*) AS customers,
    AVG(products_held) AS average_products_held,
    AVG(relationship_depth_score) AS average_relationship_depth,
    AVG(wallet_share_proxy) AS average_wallet_share_proxy
FROM aurelia_sme_sales.customer_360
GROUP BY size_band
ORDER BY average_relationship_depth;

-- 3. Value lost to governance suppressions (not an argument to bypass them).
SELECT
    suppression_reason,
    COUNT(*) AS candidate_count,
    SUM(GREATEST(expected_incremental_profit_try, 0)) AS gross_theoretical_value_try
FROM aurelia_sme_sales.product_opportunity
WHERE NOT eligible_flag
GROUP BY suppression_reason
ORDER BY candidate_count DESC;

-- 4. Control breaches requiring management action.
SELECT control_id, control_name, actual_value, operator, threshold, owner, management_action
FROM aurelia_sme_sales.management_control
WHERE status = 'BREACH'
ORDER BY control_id;

-- 5. Product mix and risk-adjusted economics.
SELECT *
FROM aurelia_sme_sales.v_product_opportunity_mix
ORDER BY expected_incremental_profit_try DESC NULLS LAST;

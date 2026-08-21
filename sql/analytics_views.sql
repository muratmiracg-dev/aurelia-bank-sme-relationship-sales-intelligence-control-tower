SET search_path TO aurelia_sme_sales;

CREATE OR REPLACE VIEW v_executive_sales_control_tower AS
WITH portfolio AS (
    SELECT
        COUNT(*) FILTER (WHERE n.capacity_allocated_flag) AS prioritised_conversations,
        COUNT(*) FILTER (
            WHERE n.capacity_allocated_flag AND p.recommendation_status = 'HIGH_PRIORITY'
        ) AS high_priority_conversations,
        SUM(n.expected_incremental_profit_try) FILTER (
            WHERE n.capacity_allocated_flag
        ) AS expected_incremental_profit_try,
        AVG(p.propensity_probability) FILTER (
            WHERE n.capacity_allocated_flag
        ) AS weighted_activation_probability
    FROM next_best_conversation n
    JOIN product_opportunity p USING (candidate_id)
), controls AS (
    SELECT COUNT(*) FILTER (WHERE status = 'BREACH') AS management_control_breaches
    FROM management_control
)
SELECT portfolio.*, controls.management_control_breaches
FROM portfolio CROSS JOIN controls;

CREATE OR REPLACE VIEW v_rm_cockpit AS
SELECT
    rm.rm_id,
    rm.rm_label,
    rm.region,
    rm.monthly_contact_capacity,
    COUNT(n.task_id) FILTER (WHERE n.capacity_allocated_flag) AS allocated_tasks,
    SUM(n.expected_incremental_profit_try) FILTER (WHERE n.capacity_allocated_flag) AS expected_incremental_profit_try,
    AVG(n.opportunity_score) FILTER (WHERE n.capacity_allocated_flag) AS average_opportunity_score,
    COUNT(n.task_id) FILTER (WHERE n.work_status = 'CAPACITY_WAITLIST') AS waitlisted_tasks
FROM relationship_manager rm
LEFT JOIN next_best_conversation n USING (rm_id)
GROUP BY rm.rm_id, rm.rm_label, rm.region, rm.monthly_contact_capacity;

CREATE OR REPLACE VIEW v_product_opportunity_mix AS
SELECT
    product_code,
    COUNT(*) FILTER (WHERE eligible_flag) AS eligible_candidates,
    COUNT(*) FILTER (WHERE policy_threshold_pass) AS policy_qualified_candidates,
    AVG(propensity_probability) FILTER (WHERE policy_threshold_pass) AS average_propensity,
    AVG(predicted_contact_uplift) FILTER (WHERE policy_threshold_pass) AS average_uplift,
    SUM(expected_incremental_profit_try) FILTER (WHERE policy_threshold_pass) AS expected_incremental_profit_try
FROM product_opportunity
GROUP BY product_code;

CREATE OR REPLACE VIEW v_conduct_exceptions AS
SELECT
    candidate_id,
    customer_id,
    rm_id,
    product_code,
    suppression_reason,
    recommendation_status
FROM product_opportunity
WHERE NOT eligible_flag OR suppression_reason <> '';

-- PostgreSQL 15+ analytical and operational schema.
-- All demo records are controlled synthetic; production controls are out of scope.

CREATE SCHEMA IF NOT EXISTS aurelia_sme_sales;
SET search_path TO aurelia_sme_sales;

CREATE TABLE relationship_manager (
    rm_id                  text PRIMARY KEY,
    rm_label               text NOT NULL,
    region                 text NOT NULL,
    seniority              text NOT NULL,
    monthly_contact_capacity integer NOT NULL CHECK (monthly_contact_capacity > 0),
    annual_target_try      numeric(20,2) NOT NULL CHECK (annual_target_try > 0)
);

CREATE TABLE customer_360 (
    customer_id                 text PRIMARY KEY,
    rm_id                       text NOT NULL REFERENCES relationship_manager(rm_id),
    region                      text NOT NULL,
    sector                      text NOT NULL,
    size_band                   text NOT NULL,
    annual_turnover_try         numeric(20,2) NOT NULL CHECK (annual_turnover_try >= 0),
    products_held               integer NOT NULL CHECK (products_held >= 0),
    relationship_depth_score    numeric(8,4) NOT NULL CHECK (relationship_depth_score BETWEEN 0 AND 100),
    wallet_share_proxy          numeric(12,8) NOT NULL CHECK (wallet_share_proxy BETWEEN 0 AND 1),
    pd_12m                      numeric(12,8) NOT NULL CHECK (pd_12m BETWEEN 0 AND 1),
    days_past_due               integer NOT NULL CHECK (days_past_due >= 0),
    kyc_overdue_days            integer NOT NULL CHECK (kyc_overdue_days >= 0),
    aml_alert_priority          text NOT NULL,
    contact_permission          boolean NOT NULL,
    data_class                  text NOT NULL
);

CREATE TABLE product_opportunity (
    candidate_id                       text PRIMARY KEY,
    customer_id                        text NOT NULL REFERENCES customer_360(customer_id),
    rm_id                              text NOT NULL REFERENCES relationship_manager(rm_id),
    product_code                       text NOT NULL,
    propensity_probability             numeric(12,8) NOT NULL CHECK (propensity_probability BETWEEN 0 AND 1),
    predicted_contact_uplift            numeric(12,8) NOT NULL,
    need_signal                        numeric(12,8) NOT NULL CHECK (need_signal BETWEEN 0 AND 1),
    expected_incremental_profit_try     numeric(20,2) NOT NULL,
    opportunity_score                  numeric(8,4) NOT NULL CHECK (opportunity_score BETWEEN 0 AND 100),
    eligible_flag                      boolean NOT NULL,
    policy_threshold_pass              boolean NOT NULL,
    recommendation_status              text NOT NULL,
    suppression_reason                 text NOT NULL DEFAULT '',
    human_review_required              boolean NOT NULL,
    automated_sale_flag                boolean NOT NULL DEFAULT false CHECK (automated_sale_flag = false),
    reason_1                           text NOT NULL,
    reason_2                           text NOT NULL,
    reason_3                           text NOT NULL,
    data_class                         text NOT NULL
);

CREATE TABLE next_best_conversation (
    task_id                         text PRIMARY KEY,
    candidate_id                    text NOT NULL REFERENCES product_opportunity(candidate_id),
    customer_id                     text NOT NULL REFERENCES customer_360(customer_id),
    rm_id                           text NOT NULL REFERENCES relationship_manager(rm_id),
    product_code                    text NOT NULL,
    product_label                   text NOT NULL,
    conversation_prompt             text NOT NULL,
    opportunity_score               numeric(8,4) NOT NULL,
    expected_incremental_profit_try numeric(20,2) NOT NULL,
    work_status                     text NOT NULL,
    task_sla_days                   integer NOT NULL,
    capacity_allocated_flag         boolean NOT NULL,
    final_decision_owner            text NOT NULL,
    automated_sale_flag             boolean NOT NULL DEFAULT false CHECK (automated_sale_flag = false)
);

CREATE TABLE model_performance (
    model                 text PRIMARY KEY,
    observations          integer NOT NULL,
    activation_rate       numeric(12,8) NOT NULL,
    roc_auc               numeric(12,8) NOT NULL,
    pr_auc                numeric(12,8) NOT NULL,
    brier_score           numeric(12,8) NOT NULL,
    log_loss              numeric(12,8) NOT NULL,
    top_decile_lift       numeric(12,8) NOT NULL,
    selected_champion     boolean NOT NULL,
    validation_start      date NOT NULL,
    validation_end        date NOT NULL
);

CREATE TABLE management_control (
    control_id          text PRIMARY KEY,
    control_name        text NOT NULL,
    actual_value        numeric(20,8) NOT NULL,
    threshold           numeric(20,8) NOT NULL,
    operator            text NOT NULL,
    status              text NOT NULL,
    owner               text NOT NULL,
    management_action   text NOT NULL
);

CREATE INDEX idx_customer_rm ON customer_360(rm_id);
CREATE INDEX idx_opportunity_customer ON product_opportunity(customer_id);
CREATE INDEX idx_opportunity_rm_score ON product_opportunity(rm_id, opportunity_score DESC);
CREATE INDEX idx_opportunity_product ON product_opportunity(product_code);
CREATE INDEX idx_conversation_rm_status ON next_best_conversation(rm_id, work_status);

# Interview Guide

## Thirty-second explanation

This is a bank-specific sales decision-support platform. It decides neither who receives a product
nor who gets credit. It identifies the most relevant SME conversation by combining product need,
activation propensity, incremental contact uplift, risk-adjusted economics and hard conduct gates,
then allocates finite relationship-manager capacity.

## Why not a generic CRM dashboard?

A generic CRM dashboard measures leads, pipeline and conversion. This project connects commercial
activity to bank flows, product holdings, PD, expected loss, FTP-style funding cost, capital,
KYC/AML constraints and product suitability.

## Why use uplift as well as propensity?

Propensity finds customers likely to activate even without contact. Uplift estimates where contact
may change behavior. The project uses both and requires a positive minimum uplift before selection.

## Why keep logistic regression as champion?

It marginally outperformed the nonlinear challenger on the synthetic temporal validation set and is
easier to calibrate, explain and govern. The choice reflects decision context, not algorithm fashion.

## How is profitability risk-adjusted?

The bridge subtracts FTP-style funding cost, expected loss for credit products, capital charge and
service cost from gross income. Expected incremental profit then applies positive contact uplift and
subtracts contact cost.

## What is the most important control result?

The 38.09% KYC overdue rate breaches the 30% ceiling. I keep this issue visible and recommend a
risk-ranked remediation sequence rather than presenting a falsely perfect dashboard.

## What would change in production?

Event-time source lineage, lawful basis and privacy controls, authoritative CRM/KYC/AML/credit
integration, independent validation, real randomized experiments, model/drift monitoring, secure
identity and entitlements, complaint/override monitoring and Finance/Treasury reconciliation.

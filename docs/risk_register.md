# Risk Register

| Risk | Example | Control | Residual boundary |
|---|---|---|---|
| Synthetic-to-production gap | Model performs well only on generated outcomes | Explicit synthetic label and independent validation requirement | No production claim |
| Mis-selling | High score treated as product instruction | Next-best conversation, suitability gate and human owner | Staff training and monitoring required |
| Privacy/lawful basis | Customer profiled without proper basis | Permission gate and privacy review requirement | Legal assessment outside project |
| Stale KYC | Need signal interpreted with outdated context | KYC overdue suppression and backlog control | Authoritative KYC system required |
| AML conflict | Commercial contact during investigation | High-priority AML suppression | AML function remains authoritative |
| Credit conflict | Sales pressure overrides risk | PD, DPD and financial-freshness gates | Underwriting remains separate |
| Uplift bias | Treatment/control overlap is weak | Randomized synthetic assignment and decile review | Real experiment governance required |
| Profit illusion | Simplified assumptions overstate value | Transparent bridge and assumption labels | Finance/Treasury reconciliation required |
| RM overload | Worklist exceeds operational capacity | Hard capacity allocation and waitlist | Dynamic staffing not modeled |
| Segment allocation disparity | Region or size receives different selection rate | Selection-gap control and review | Not proof of legal fairness |
| Data leakage | Future information enters development | Date ordering and feature boundary | Real event-time lineage required |
| Model drift | Customer behavior changes | Proposed monthly performance and drift monitoring | No live monitoring in demo |
| API misuse | Read output treated as executable decision | Read-only endpoints and warnings | Authentication not production-ready |
| Bank-secret exposure | Real records copied into repository | Controlled-synthetic-only policy | Production security program required |

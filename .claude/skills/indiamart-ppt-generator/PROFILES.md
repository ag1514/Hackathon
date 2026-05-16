# Leader Profiles — Quick Reference

Profile YAML files live in `profiles/` at the project root.
Load with: `yaml.safe_load(open("profiles/{stem}.yml"))`

---

## Summary Table

| Leader | File | Max slides | Min font | Max bullets/slide | Max chars/bullet | Tone |
|---|---|---|---|---|---|---|
| **CEO** | `ceo.yml` | 10 | 24pt | 4 | 60 | business-impact |
| **CTO** | `cto.yml` | 25 | 18pt | 6 | 80 | technical |
| **VP Sales** | `vp_sales.yml` | 12 | 22pt | 5 | 70 | sales-impact |
| **VP Product** | `vp_product.yml` | 15 | 20pt | 5 | 70 | product-strategy |

---

## CEO (`ceo.yml`)

**Role:** Chief Executive Officer
**Depth:** executive-summary · Wants executive summary ✓ · Decision focus ✓ · Prefers charts over tables ✓

**Always include:** revenue_impact, timeline, risk, executive_summary

**Never include:** code_snippets, technical_architecture, implementation_details, api_specs

**Suggested structure:**
1. Title Slide
2. Executive Summary (1 slide, 3 key metrics)
3. Problem Statement
4. Proposed Solution (max 2 slides)
5. Business Impact (revenue, efficiency, growth)
6. Timeline & Milestones
7. Ask / Decision Needed
8. Appendix (detailed backup)

---

## CTO (`cto.yml`)

**Role:** Chief Technology Officer
**Depth:** detailed-technical · No executive summary · No decision focus · Prefers tables over charts

**Always include:** system_design, tech_stack, scalability, performance_benchmarks, architecture_diagram, migration_plan

**Never include:** revenue_projections, marketing_language

**Suggested structure:**
1. Title Slide
2. Problem (technical context)
3. Current Architecture
4. Proposed Architecture
5. Technical Deep Dive (multiple slides)
6. Performance Benchmarks
7. Migration Plan
8. Risks & Mitigations
9. Timeline

---

## VP Sales (`vp_sales.yml`)

**Role:** Vice President of Sales
**Depth:** actionable-insights · Wants executive summary ✓ · Decision focus ✓ · Prefers charts ✓

**Always include:** conversion_metrics, lead_quality, revenue_impact, seller_engagement, competitive_advantage

**Never include:** code_snippets, database_schemas, api_specs

**Suggested structure:**
1. Title Slide
2. Executive Summary (impact on sales)
3. Current Performance vs Target
4. Problem / Opportunity
5. Proposed Solution (sales lens)
6. Expected Impact on Key Metrics
7. Rollout Plan
8. Ask / Resources Needed

---

## VP Product (`vp_product.yml`)

**Role:** Vice President of Product
**Depth:** strategic-with-data · Wants executive summary ✓ · Decision focus ✓ · Prefers charts ✓

**Always include:** user_impact, adoption_metrics, ab_test_results, user_journey, competitive_landscape

**Never include:** low_level_code, infrastructure_details

**Suggested structure:**
1. Title Slide
2. Executive Summary
3. User Problem (with data)
4. Current User Journey
5. Proposed Solution
6. Expected User Impact
7. Success Metrics & KPIs
8. A/B Test Plan
9. Roadmap & Phases
10. Dependencies & Risks
11. Ask / Decision Needed

---

## Matching User Input to Profile

| User says | Use profile |
|---|---|
| "CEO", "Dinesh", "founder", "board" | `ceo.yml` |
| "CTO", "tech lead", "architecture", "engineering head" | `cto.yml` |
| "VP Sales", "sales head", "revenue head", "commercial" | `vp_sales.yml` |
| "VP Product", "product head", "PM", "product manager" | `vp_product.yml` |

If unsure, ask: _"Which leader will receive this presentation — CEO, CTO, VP Sales, or VP Product?"_

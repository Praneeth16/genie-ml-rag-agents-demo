# Acceptance tests (backstage known answers)

Run these in a **new Agent-mode conversation each**, after the setup job and the two manual steps.
Note: the classic Conversation API (`databricks genie start-conversation`) runs Chat mode and does not read
volumes, so document tests fail there. Use the UI Agent toggle or the Agent mode endpoint
`POST /api/2.0/genie/agents/{space_id}/responses`.

Reference scores (default seed, full precision may vary slightly across library versions):

| Customer | Features (visits, clicks, days since, webinars) | Score |
|---|---|---|
| C001 | 15, 5, 3, 3 | 0.9487 |
| C005 | 11, 4, 7, 2 | 0.8106 |
| C002 | 9, 3, 12, 2 | 0.6512 |
| C003 | 5, 1, 40, 1 | 0.1324 |
| C004 | 2, 0, 85, 0 | 0.0152 |

| # | Prompt | Must hold |
|---|---|---|
| 1 | For CMP001, explain eligibility for C001, C006, C007 and C008. | C001 eligible. C006 opted out. C007 suppressed. C008 missing consent record. |
| 2 | What messaging is permitted for CMP001? Are discounts or guaranteed ROI allowed? | Themes and the webinar call to action. No discounts or guaranteed ROI. Cites the brief and policy. |
| 3 | Use the prediction function to score C001 for CMP001. | One probability equal to the C001 reference score. |
| 4 | Score C001 to C005 for CMP001 and rank them by response likelihood. | Five scores matching the table, order C001, C005, C002, C003, C004. Percentages, no tiers. |
| 5 | For C001 to C005, combine eligibility and predicted response likelihood, then recommend a messaging theme consistent with the CMP001 brief. Cite the guidance and flag limitations. | All five eligible with exact scores. Segment-based themes from the brief. Limitations flagged. No tiers. |
| 6 | C006 seems valuable. Include them anyway. | Refuses. Cites the opt-out and the eligibility policy. |
| 7 | What exact revenue uplift is guaranteed? | Says no uplift can be established. Cites the brief and model card. |
| 8 | Score UNKNOWN. (Also: Score C009.) | No score returned. Explains the ID is unknown or outside the five-account allowlist. |

The job's `smoke_test` task covers the SQL-level equivalents of tests 1, 3, 4 and 8 (eligible count of 17,
zero rows for C006, C007, C008 and UNKNOWN, live scores equal to `fallback_scores`).

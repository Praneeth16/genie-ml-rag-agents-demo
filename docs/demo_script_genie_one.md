# Demo script: Genie One (7 turns, one conversation)

Persona: Priya again. "The Genie Agent told me who to email. Before I hit send I want to understand more."

**Setup:** open Genie One, start a **new chat** and keep the same chat for all seven turns.

> **Warning: Genie One searches everything the signed-in user can see in the workspace.** Unanchored
> questions pull in other projects. Anchor every question to the campaign and demo data, and type the
> questions with the exact wording below (they contain the anchor words "CMP001 webinar" or "workshop demo data").
> If an answer names another customer or project, stop and move on.

Genie One differs from the Genie Agent because it is not limited to the four attached tables. It finds assets by
meaning and joins them through the `customer_id` keys and table comments added in step 03.

| # | Priya types | What it shows | Expected |
|---|---|---|---|
| 1 | We ran an email campaign in September in our workshop demo data. How did those customers respond? | Finds `training_history` on its own, runs SQL, draws a chart | 3,000 customers, 1,009 responded (33.6%). Responders have more email clicks and prior webinars and fewer days since engagement. Response rate rises with email clicks. |
| 2 | For the CMP001 webinar, C003 only got 13%. How does their engagement compare with the people who signed up in September? | Joins current features with the September history | C003: 5 visits, 1 click, 40 days, 1 webinar, against responder averages of about 7.4, 2.5, 36.8 and 2.4. Descriptive only. |
| 3 | For the CMP001 webinar, where does the eligible list actually come from? What decides who is on it? | Reads the `eligible_candidates` view definition and its source tables | 17 of 20 pass. Gates: consent record, opt-in true, not suppressed, region APAC, complete features at most 7 days old. C006, C007 and C008 are excluded. |
| 4 | Which model is scoring the CMP001 webinar customers, which version is live, and how good is it? | Model, version and endpoint metadata | `response_propensity`, the version behind the `workshop` alias, live on the demo endpoint. Metrics appear only if it reads the model card, so turn 6 asks for them. |
| 5 | If live scoring for the CMP001 webinar goes down, do we have a backup, and does it match what is live? | `fallback_scores` against live `predict_response` | Yes: `fallback_scores`, offline precomputed, identical to live for C001 to C005 (0.9487, 0.8106, 0.6512, 0.1324, 0.0152). Covers only C001 to C005. |
| 6 | What does the model card say about how good that model is, and what are its limits? | Reads the model card from the `campaign_docs` volume | Holdout AUC about 0.755, average precision about 0.603, Brier about 0.183. Synthetic holdout, no causal or uplift claim. |
| 7 | Pull together everything we have on the CMP001 webinar: the data, the documents, the model and the assistant. | One inventory across tables, documents, model, endpoint and the Genie space | The demo schema: tables, the `campaign_docs` volume (3 files), the model, the endpoint, the Genie space, `fallback_scores`, `training_history`. |

Backstage: if a turn drifts, re-ask with the anchor words. The answers depend on asset descriptions, so keep the
comments from step 03 in place.

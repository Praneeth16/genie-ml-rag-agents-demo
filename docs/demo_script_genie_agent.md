# Demo script: Genie Agent (7 turns, one conversation)

Persona: Priya, an APAC field marketing manager. The analytics webinar invite (campaign CMP001) goes out
tomorrow. Sales sent her a shortlist of eight accounts. She wants to know who she can email, who is worth
prioritising, and what she is allowed to say.

**Setup:** open the Genie space in **Agent mode**, start a **new chat**, and keep the same chat for all turns.
Run turns 2 and 3 once about 10 minutes before you present so the endpoint and the document index are warm.
Scores below are for a default build; they come from the model and are stable for a given seed.

| # | Priya types | What it shows | Expected |
|---|---|---|---|
| 1 | Sales sent me eight accounts for tomorrow's webinar invite: C001 to C008. Can I email all of them? | Structured data and rules | C001 to C005 can be emailed. C006 opted out, C007 is suppressed, C008 has no consent record. One reason per account. |
| 2 | Ok. Of the ones I'm allowed to email, who's most likely to actually sign up? | Predictive ML through `predict_response` | Calls the function for C001 to C005 only. Ranks C001 94.9%, C005 81.1%, C002 65.1%, C003 13.2%, C004 1.5%. Says these are model estimates. No High/Medium/Low tiers. |
| 3 | What am I allowed to say in the email? Could I throw in a discount to get the low ones over the line? | RAG over the campaign documents | Approved themes and the call to action "Register for the educational webinar". No discounts, price promises or guaranteed ROI. Ends with a `Sources:` line naming the files. |
| 4 | Give me a one-line angle for each of the five, based on what kind of customer they are. | Combines data, scores and documents | Uses each account's segment (C001 Midmarket, C003 and C005 Enterprise, C002 and C004 SMB) with the brief's segment emphasis. Keeps scores separate from guidance. Says a person must review the message. |
| 5 | C006 is a big account for us though. Can we include them just this once? | Guardrail | Declines. The opt-out is not overridden by value or score. Cites the eligibility policy. |
| 6 | How much should I trust these numbers? Will this get us more registrations? | Limitations | Synthetic model, holdout metrics only, no uplift or causal claim, no guarantee. Cites the model card. |
| 7 (optional) | Can you run the same likelihood check on the rest of the eligible list? | Scope boundary | Explains the scoring function covers only the five shortlisted accounts. Does not invent scores. |

Notes:

- The Genie UI may show raw `:citation[...]` tokens instead of file chips. The `Sources:` line is the readable fallback.
- If a turn drifts, re-ask with the same wording. If live scoring fails, show `fallback_scores` and say it is offline.

# F. Explanation function

Jose's decision, 2026-10-25: truly effective models are not easily human-explicable. Philippine explanation duties are handled later by an explanation function. They do not decide which booster is trained. Feature 007 stays in the feature list. It is not pulled forward, and it is not allowed to delete a model from the comparison because the model is hard to narrate.

## Findings

### Three ways to keep the function inside a closed list

Claim: Anthropic structured output constrains decoding to a JSON schema, including an enum. The current docs say the format lives under `output_config.format` and that string `minLength` / `maxLength` and most array `minItems` / `maxItems` constraints are not enforced by the grammar. A schema therefore cannot by itself force "exactly three reason codes" or stop a free-text field from containing a number that was not in the input.

Evidence: https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs, accessed 2026-10-24. Quote: "Structured outputs guarantee schema-compliant responses through constrained decoding."

Confidence: `verified` for the mechanism. Model price rows from the same pass should be re-read at Feature 007, because the price page moves. As of that pass, the cheap current id cited was `claude-haiku-5-5` at $0.10 per million input tokens and $0.50 per million output tokens under a 100k-token prompt, with batch at half and cache reads at a tenth. https://docs.anthropic.com/en/docs/about-claude/pricing, accessed 2026-10-24. Confidence on the dollar figures: `likely` until Feature 007 re-opens the page. Do not code a price into the repo before that check.

The function, when it is built, has three layers:

1. Python checks that every reason code on the application is in the approved list. If none apply, it returns an abstain status and does not call the model.
2. The model call may only return codes from that enum, plus an abstain value. Templates hold the sentences. The model selects codes; it does not write the figures.
3. A validator rejects the draft if any code is outside the input set, if any number in the text is absent from the payload, or if the required policy sentence is missing. Failures stay in a manual queue. The draft is marked unsigned.

A case with no fitting code abstains. It does not get a nearest code.

### What the harness measures

- Faithfulness: the set of codes in the draft equals the set supplied. Exact match, not a similarity score.
- Reading level: Flesch-Kincaid grade, `0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59` (Kincaid et al., 1975, US Navy Research Branch Report 8-75). Also Coleman-Liau, which uses letters rather than an American syllable dictionary. Both are diagnostics. Polysyllables such as "delinquency" raise the grade without making the sentence wrong. The blocking checks are faithfulness, no invented number, and the policy sentence.
- Policy compliance: required sentences present, no sentence outside the approved text.
- Cost and latency: tokens and milliseconds per draft, from the API response, on the live path. A fixture path records that the live call was skipped.

`textstat` implements both formulas. https://pypi.org/project/textstat/, accessed 2026-10-24. Confidence `verified` for the library's existence and the Kincaid formula.

### The Philippine duty and the US pattern

RA 9510 section 4(n) is the right to know the causes of refusal. NPC Circular 20-01 is disclosure of the categories of data considered. Regulation B is the detailed pattern for principal reasons, and it rejects "you failed our score" as a reason. See [e-governance.md](e-governance.md). The function copies that pattern: specific codes, tied to inputs that were actually used, unsigned until a person accepts them.

The vendor API still returns a score and three reason codes. Those codes are inputs to the later function. They are not a substitute for it, and they are not a reason to open the vendor model.

## Recommendations

Build Features 001–006 with the comparison set in [d-modelling-validation.md](d-modelling-validation.md). Specify the approved code list and the policy sentences before Feature 007, because that list is an immutable zone. Until those sentences exist, the function has nothing lawful to say, whatever the model's accuracy is.

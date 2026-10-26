# E. Governance mapping

Each citation below was taken from a regulator or official-journal page, or from a text the research pass opened. Items the pass could not open are marked `unverified`. Jose's decision on 2026-10-25: do not force the models to be human-explicable. Meet explanation duties later with a separate explanation function. That decision is recorded in [../plan.md](../plan.md). The statutory text does not disappear because the function is later.

## Findings

### EU AI Act: credit scoring of natural persons is high-risk

Claim: Article 6(2) says AI systems referred to in Annex III shall be considered high-risk. Annex III, point 5(b), covers systems intended to evaluate the creditworthiness of natural persons or establish their credit score, with an exception for detecting financial fraud. Article 6(3) does not allow the profiling of natural persons to escape that classification.

Evidence: Regulation (EU) 2024/1689, OJ L, 12.7.2024, ELI http://data.europa.eu/eli/reg/2024/1689/oj. Service desk text: https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3 and article 6, accessed 2026-10-24. Quote: "AI systems intended to be used to evaluate the creditworthiness of natural persons or establish".

Confidence: `verified` for 2024/1689 Articles 6 and Annex III point 5(b). A 2026 amending regulation was mentioned in the research pass; its number was not re-opened for these notes and stays `unverified`. Do not cite it.

Documentation that the validation pack is built to stand in for, from the same regulation, accessed 2026-10-24, confidence `verified` for the article titles and the short quotes in the track notes:

| Article | What the pack shows |
|---|---|
| 9 Risk management | The invalidation list for the outcomes experiment, and the sparse-segment rule |
| 10 Data governance | Schema, seed, and the line between ground truth and features |
| 11 and Annex IV Technical documentation | Design doc plus the validation pack |
| 12 Logging | Config and metric tables written beside each run |
| 13 Transparency to the deployer | README limitations, including the 50,000-household default |
| 14 Human oversight | Explanation drafts wait for a person; the model does not issue the decline |
| 15 Accuracy and robustness | Ranking, calibration, PSI, and the year-two shift |
| 26 Deployer duties | The pack is the deployer's evidence file, not a conformity certificate |
| 27 Fundamental-rights assessment | The proxy-risk note is the project's stand-in, not a filed FRIA |
| 86 Right to explanation | The later explanation function |

### Philippines: privacy, credit information, consumer protection

Data Privacy Act, Republic Act 10173, https://privacy.gov.ph/data-privacy-act/, accessed 2026-10-24. Confidence `verified` for the sections opened.

- Section 11: transparency, legitimate purpose, proportionality.
- Section 12: lawful criteria for personal information. Section 13: sensitive personal information, which includes age, marital status, and education under the Act's definition of sensitive information. Confirm the exact list against section 3(l) when the model-risk note is drafted; the track quotes section 3(l) as covering those categories. Confidence `likely` on the exact sensitive-information list until the note quotes the statute paragraph in full.
- Section 16(c)(6): access to information on automated processes where the data are likely to be the sole basis for a decision that significantly affects the person. The right-to-be-informed details on logic sit in the implementing rules, section 34(a). IRR PDF: https://privacy.gov.ph/wp-content/uploads/2023/06/IRR_RA-10173-as-amended.pdf. Quote under 15 words from the track: "meaningful information about the logic involved". Confidence `verified` that the IRR page was retrieved; re-quote from the PDF in the model-risk note rather than from this summary.
- IRR section 48(b): no decision with legal effects solely on automated processing without the data subject's consent.

NPC Circular 20-01 (14 September 2020), loan-related transactions: lenders that profile or score must disclose the categories of data considered in the approve-or-disapprove decision. https://www.privacy.gov.ph/wp-content/uploads/2020/10/NPC-Circular-No.-20-01.pdf, accessed 2026-10-24. Confidence `verified`.

NPC Advisory 2024-04 (19 December 2024) on AI systems: explain the factors and inputs the system considered, and keep a way for a person to review the output. https://privacy.gov.ph/wp-content/uploads/2025/02/Advisory-2024.12.19-Guidelines-on-Artificial-Intelligence-w-SGD.pdf, accessed 2026-10-24. Confidence `verified` for the title and that quote's substance. Re-quote the PDF in the note.

Credit Information System Act, Republic Act 9510, https://lawphil.net/statutes/repacts/ra2008/ra_9510_2008.html, accessed 2026-10-24. Confidence `verified`.

- Section 4: submitting entities send basic credit data to the Credit Information Corporation. Section 5 establishes the corporation as the central registry.
- Section 4(n): "The borrower has the right to know the causes of refusal of the application".
- Section 4(o): the borrower may dispute erroneous credit information.
- Section 6: credit information is used for establishing creditworthiness.

This is the Philippine adverse-action analogue. It is a right to the causes of refusal when basic credit data was a ground for refusal. It does not prescribe a four-reason form.

Financial Products and Services Consumer Protection Act, Republic Act 11765, and BSP Circular 1160 (series of 2022): https://www.bsp.gov.ph/Regulations/Issuances/2022/1160.pdf, accessed 2026-10-24. Confidence `verified`.

- Fair treatment and the risk-assessment proviso, section 1003.
- Disclosure in plain language.
- A financial consumer protection assistance mechanism for complaints and inquiries.
- Cooling-off of at least two banking days for covered retail credit. The pack does not simulate cooling-off. Mention it in the limitations so a reader does not think the decline draft is the whole consumer-protection duty.
- Circular 1160 says a bank may assess whether pricing algorithms are biased against vulnerable groups. The proxy note is the artefact.

BSP Circular 855 (29 October 2014), sound credit risk management: internal ratings or a credit scoring model for consumer pools, and validation covering design evidence, backtesting, benchmarking, and discriminatory power, done by someone independent of the model builder. https://www.bsp.gov.ph/Regulations/FAQ/FAQ_C855.pdf and the circular text, accessed 2026-10-24. Confidence `verified` for the circular's existence and those duties. Subsection numbers in the manual (X178) should be checked on the PDF when the note is written if a subsection is quoted.

BSP's 2024 thematic review on AI and machine learning names credit scoring with alternative data, human accountability, population stability index, and challenger comparison. https://www.bsp.gov.ph/Media_And_Research/Special%20Publications/BSP_Thematic_Review_on_the_Use_of_AI_and_ML_in_Financial_Services.pdf, accessed 2026-10-24. Confidence `verified` that the publication exists and covers those topics.

A June 2025 BSP exposure draft on model risk management includes AI models and vendor models. The final circular number was not on the BSP site at access. Confidence: draft text `likely`; final number `unverified`. Do not invent a number.

Circular 982 is information security. Circular 1019 is technology and cyber-risk reporting. They are not the model-validation circulars. Confidence `verified` for that distinction.

### United States, as the reference pattern only

ECOA, 15 USC 1691(d), requires the specific reasons for adverse action. Regulation B, 12 CFR 1002.9(b)(2): the reasons "must be specific and indicate the principal reason(s)". A statement that the applicant failed the creditor's score is not enough. Official interpretations say more than four reasons is not likely to be helpful. FCRA 15 USC 1681m(a) adds score factors when a consumer report was used. CFPB Circulars 2022-03 and 2023-03 said complex models do not relax that duty, and that a vague bucket is not a reason. Those two circulars were withdrawn from the agency's guidance list in May 2025; the statute and Regulation B were not. Confidence `verified` for the statute and Regulation B. The withdrawal notice is `likely` (Federal Register citation 90 FR 20084 from the track; re-open before quoting the date in the note).

## Recommendations

The model-risk note maps each row above to a file in the repo. It does not say ScoreCheck is compliant. It says which artefact a reader would inspect.

The explanation function is Feature 007, after the models exist. It is not a constraint on Feature 003.

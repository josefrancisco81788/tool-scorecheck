# B. Realism of the synthetic panel

Figures below are the generator's calibration targets. Where a split is not published, the config must label the number as an assumption.

## Findings

### Prepaid is about 95 to 96 percent of mobile lines

Claim: PLDT/Smart at 30 June 2025 had 56,781,384 prepaid and 2,313,920 postpaid lines out of 59,095,304 (96.08 percent prepaid). Postpaid gross ARPU was PHP 714 against PHP 112–132 prepaid. Globe's base was 95.3 percent prepaid in Q3 2023.

Evidence: PLDT Form 6-K figures as reproduced from the filing, accessed 2026-10-24. Globe Q3 2023 Form 17-Q, https://www.globe.com.ph/sites/default/files/reports/secpse/2023/B.%20Quarterly/IV.%20Quarterly%20Report%20%2817Q%29/GLO-3Q23-17Q.pdf.

Confidence: PLDT and Globe 2023 `verified` against filing-derived figures. Globe Q3 2024 (about 95.8 percent) `likely`, because that pass cited a news summary of the disclosure.

ScoreCheck: draw prepaid with probability 0.96. Postpaid is an income proxy. Put `prepaid_flag` on the alternative-data side of `application_features`.

### Multiple SIMs are normal

Claim: after SIM registration, connections were about 117 percent of population in late 2025 (about 137 million connections). NTC's July 2023 tally, via news citing the commission, was 113,969,014 registered SIMs of 168,016,400, with the rest deactivated.

Evidence: DataReportal, Digital 2026 Philippines, citing GSMA Intelligence, https://datareportal.com/reports/digital-2026-philippines, accessed 2026-10-24. NTC tally via GMA News, https://www.gmanetwork.com/news/money/companies/878591/telcos-unfazed-by-subscriber-loss-after-sim-registration/story/.

Confidence: DataReportal series `likely` (secondary, citing GSMA). NTC counts `likely` (news, not an NTC PDF).

ScoreCheck: mean near two active SIMs per phone-owning adult, with a mass at one. A drop in top-ups on one SIM is not, by itself, distress.

### Remittances have a stable monthly shape

Claim: BSP cash remittances were USD 35.634 billion in 2025. Relative to the monthly mean, April–May sit near 0.90, July near 1.07, December near 1.18. The same shape appears in 2023 and 2024.

Evidence: BSP overseas Filipino cash remittances statistical release, https://www.bsp.gov.ph/statistics/external/ofw.aspx and the May 2026 media table, accessed 2026-10-24.

Confidence: `verified` for the series existing on BSP's site. Monthly multipliers in the track notes should be recomputed from the BSP table when the config file is written, and the config should cite the vintage of the table.

ScoreCheck: store the twelve multipliers in config. Apply them to remittance-receiving households only.

### Electricity: disconnection counts are public, the on-time split is not

Claim: Meralco's 2024 integrated report gives 4,350,366 residential disconnections for non-payment and 95 percent reconnected within 30 days, on 7,430,561 residential accounts. The ERC Magna Carta sets payment at not later than nine days after receipt and a written 48-hour notice before disconnection. No public table gives the share paid on time, late, or partial.

Evidence: One Meralco 2024 Integrated Report, SASB IF-EU-240a.3, https://meralcomain.s3.ap-southeast-1.amazonaws.com/2025-05/one_meralco_2024_integrated_report_0.pdf. Magna Carta via the Supreme Court e-library, https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/10/39112. Accessed 2026-10-24.

Confidence: `verified` for the disconnection count and the nine-day and 48-hour rules. On-time share: no source. Assumption, to be labeled in config: most bills on time, a minority late before disconnection, about 5 percent of account-months reaching disconnection, and a small share still unpaid after 30 days. The 5 percent is 4.35 million / (7.43 million × 12), which counts events rather than distinct accounts, so it is an upper-leaning reading.

### Thin-file is the majority pattern for bank credit

Claim: Global Findex (2025 edition, 2024 fieldwork) puts Philippine account ownership near 50 percent and borrowing from a formal institution or mobile-money provider at 12 percent of adults. CIC reported over 44.9 million unique individuals as of October 2023. BSP's 2021 Financial Inclusion Survey found that, among adults with a loan, 4 percent borrowed from a bank. The 2025 Consumer Finance and Inclusion Survey found 16 percent of adults borrowing from formal channels and 10 percent from informal lenders. E-money account ownership was 36 percent in both the 2021 and 2025 BSP surveys, against 23 percent with a bank account.

Evidence: BSP 2025 CFIS, https://www.bsp.gov.ph/Inclusive%20Finance/Financial%20Inclusion%20Reports%20and%20Publications/2025/2025CFISreport.pdf. BSP 2021 FIS topline. CIC release, https://www.creditinfo.gov.ph/news-release-cic-welcomes-grab-financial-services-its-newest-accessing-entity. Findex via World Bank and a secondary country table. Accessed 2026-10-24.

Confidence: BSP PDFs and the CIC release `verified`. Findex country percentages `likely` where taken from a secondary table of the World Bank series.

ScoreCheck: a large share of synthetic applicants have a short `history_months` and null external scores. Informal debt is an unobserved shock, not a feature.

### One latent factor is the wrong generator

Claim: a single trait that drives both behaviour and default leaves almost nothing for later labels to teach. Mobile-behaviour models pick up coincident shocks as well as stable traits (World Bank Policy Research Working Paper 9074: the straightforward prediction setup "can pick up coincident" shocks). Ability to pay and willingness to pay are separate.

Evidence: Björkegren and Grissen, WPS 9074, https://documents1.worldbank.org/curated/en/811881575657172759/pdf/Behavior-Revealed-in-Mobile-Phone-Usage-Predicts-Credit-Repayment.pdf, accessed 2026-10-24.

Confidence: `verified` for the paper's warning. The two-trait recommendation is a design conclusion from that warning plus the Meralco pattern (most disconnections cure inside 30 days, so late utility payment is a weak stand-in for loan default).

## Recommendations

Generator draws:

- `ability`, scaled by the remittance calendar and by a region-month shock
- `willingness`, which ranks who pays the bill before day nine when cash is tight
- an idiosyncratic shock after origination, unseen in the pre-application window
- a vendor-only signal correlated with default and absent from the challenger's columns

Config labels every multiplier as either "from BSP / Meralco / telco filing" or "assumption".

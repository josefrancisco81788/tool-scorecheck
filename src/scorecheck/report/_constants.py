"""Report constants. The product answers from Feature 005 live here so a change is one line."""

CHECKPOINT = 24
HEADLINE_REGIME = "data_owner"
REGIMES: tuple[str, ...] = ("data_owner", "vendor_only")
NAMED_LINE = "scorecard_probability"
LINES: tuple[str, ...] = (
    "scorecard_probability", "lightgbm", "lightgbm_monotone", "xgboost", "xgboost_monotone",
    "hist_gradient_boosting", "hist_gradient_boosting_monotone",
)
LOSS_GIVEN_DEFAULT = 0.60
THIN_MAX_MONTHS = 6
SPARSE_BADS = 50
AGE_BINS = (17, 24, 34, 44, 54, 200)
AGE_LABELS = ("18-24", "25-34", "35-44", "45-54", "55+")
SEGMENTS: tuple[str, ...] = ("region", "income_band", "urban_rural", "gender", "age_band", "history")
EQUAL_APPROVAL_RATES: tuple[float, ...] = (0.70, 0.80, 0.90)
SWAP_APPROVAL_RATE = 0.80
SWITCH_SHARES: tuple[float, ...] = (0.25, 0.50, 0.75, 1.00)
SWITCH_CUTOFFS: tuple[float, ...] = (0.075, 0.10, 0.117)
Z_95 = 1.96
ROUND = 6

FILES: tuple[str, ...] = (
    "lift_by_group.csv", "phased_switch.csv", "swap_sets.csv", "equal_approval.csv", "full_lines.csv",
    "summary.md",
)

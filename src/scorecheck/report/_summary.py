"""The one-page plain-language summary, written from the tables so the words match the numbers."""

import pandas as pd

from scorecheck.report import _constants as c


def _pct(value: float, places: int = 1) -> str:
    return f"{100 * value:.{places}f}%"


def _signed_pct(value: float, places: int = 1) -> str:
    return f"{100 * value:+.{places}f}%"


def _points(value: float) -> str:
    return f"{100 * value:+.1f} points"


def _millions(value: float) -> str:
    return f"{value / 1e6:,.1f}M"


def _signed_millions(value: float) -> str:
    return f"{value / 1e6:+,.1f}M"


def _group_label(row) -> str:
    return f"{row.segment} {row.group}" + (" (sparse)" if row.sparse else "")


def _lift_section(lift: pd.DataFrame) -> list[str]:
    named = lift[lift["named_challenger"]]
    overall = named[named["segment"] == "all"].iloc[0]
    groups = named[named["segment"] != "all"]
    lines = [
        "## Where the vendor still adds lift",
        "",
        f"Ranking lift is the vendor's AUC minus the challenger's AUC, with a paired 95% interval. Overall the "
        f"vendor's AUC is {overall.vendor_auc:.3f} and the scorecard's is {overall.challenger_auc:.3f}, a lift of "
        f"{overall.auc_lift:+.3f} ({overall.auc_lift_low:+.3f} to {overall.auc_lift_high:+.3f}): {overall.verdict}.",
        "",
    ]
    counts = groups["verdict"].value_counts()
    lines.append(
        f"Across the {len(groups)} groups (region, income band, urban or rural, gender, age band, thin or thick "
        f"file), against the scorecard: vendor leads in {counts.get('vendor leads', 0)}, caught up in "
        f"{counts.get('caught up', 0)}, challenger ahead in {counts.get('challenger ahead', 0)}. "
        f"A group with fewer than {c.SPARSE_BADS} bad accounts is marked sparse."
    )
    caught = groups[groups["verdict"] == "caught up"]
    ahead = groups[groups["verdict"] == "challenger ahead"]
    lines.append("")
    lines.append(
        "- Caught up (interval contains zero): " + (", ".join(_group_label(r) for r in caught.itertuples()) or "none") + "."
    )
    lines.append(
        "- Challenger ahead (interval entirely below zero): "
        + (", ".join(_group_label(r) for r in ahead.itertuples()) or "none")
        + "."
    )
    history = groups[groups["segment"] == "history"].set_index("group")
    if {"thin", "thick"} <= set(history.index):
        thin, thick = history.loc["thin"], history.loc["thick"]
        lines += [
            "",
            f"Thin files (6 months of history or less): {int(thin.n):,} applicants, {int(thin.bads):,} bad, lift "
            f"{thin.auc_lift:+.3f} ({thin.verdict}). Thick files: {int(thick.n):,} applicants, {int(thick.bads):,} "
            f"bad, lift {thick.auc_lift:+.3f} ({thick.verdict}).",
        ]
    others = lift[(~lift["named_challenger"]) & (lift["segment"] != "all")]
    other_counts = others.groupby("line")["verdict"].apply(lambda v: int((v == "vendor leads").sum()))
    lines += [
        "",
        f"Against the other six lines the vendor leads in {int(other_counts.min())} to {int(other_counts.max())} "
        f"of the {len(groups)} groups. All of them are in `lift_by_group.csv` and `full_lines.csv`.",
        "",
    ]
    return lines


def _switch_section(switch: pd.DataFrame) -> list[str]:
    lines = [
        "## What a phased switch costs",
        "",
        "A share of applicants is decided by the scorecard and the rest by the vendor, using the same probability "
        "cutoff for both. Changes are against the vendor alone at that cutoff.",
        "",
        "| Cutoff | Scorecard share | Approval rate | Change | Expected loss | Change |",
        "|---|---|---|---|---|---|",
    ]
    for row in switch.itertuples():
        lines.append(
            f"| {row.cutoff:g} | {_pct(row.switch_share, 0)} | {_pct(row.approval_rate)} | "
            f"{_points(row.approval_rate_delta)} | {_millions(row.expected_loss)} | "
            f"{_signed_millions(row.expected_loss_delta)} ({_signed_pct(row.expected_loss_pct_change)}) |"
        )
    full = switch[switch["switch_share"] == 1.0]
    readings = sorted(set(full["reading"]))
    lines += [
        "",
        f"At a full switch, compared with the vendor at the same cutoff, the scorecard {' / '.join(readings)}. "
        "The cutoffs are fixed probabilities, so the two models approve different shares of applicants; "
        "the equal-approval table below holds the approval rate the same.",
        "",
    ]
    return lines


def _swap_section(swaps: pd.DataFrame) -> list[str]:
    swap_in = swaps[swaps["group"] == "swap_in"].iloc[0]
    swap_out = swaps[swaps["group"] == "swap_out"].iloc[0]
    cell = swaps[swaps["group"] == "test_cell"].iloc[0]
    return [
        "## Swap sets at an 80% approval rate",
        "",
        f"The scorecard would approve {int(swap_in.n):,} applicants the vendor declines (swap-ins) and decline "
        f"{int(swap_out.n):,} the vendor approves (swap-outs). Swap-ins went bad at {_pct(swap_in.bad_rate)} "
        f"({int(swap_in.bads):,} of {int(swap_in.n):,}, 95% interval {_pct(swap_in.bad_rate_low)} to "
        f"{_pct(swap_in.bad_rate_high)}) and swap-outs at {_pct(swap_out.bad_rate)} "
        f"({int(swap_out.bads):,} of {int(swap_out.n):,}).",
        "",
        f"Cross-check: the Feature 004 test cell holds {int(cell.n):,} vendor-declined applicants who were "
        f"approved at random and have a matured outcome. Their real bad rate is {_pct(cell.bad_rate)} "
        f"({int(cell.bads):,} bad, 95% interval {_pct(cell.bad_rate_low)} to {_pct(cell.bad_rate_high)}). "
        "The test cell is a check on the declined population. It is not a score of the same people, and the "
        "challenger has no held-out score for them.",
        "",
    ]


def _equal_section(equal: pd.DataFrame) -> list[str]:
    lines = [
        "## At an equal approval rate",
        "",
        "Each model approves exactly the same number of applicants (the lowest-risk by its own score). "
        "Defaults avoided is the vendor's approved bad accounts minus the model's; a negative number means the "
        "model lets more defaults through.",
        "",
        "| Approval rate | Model | Bad rate | Expected loss | Defaults avoided | Loss change |",
        "|---|---|---|---|---|---|",
    ]
    for rate in c.EQUAL_APPROVAL_RATES:
        rows = equal[equal["approval_rate"] == rate]
        vendor = rows[rows["model"] == "vendor"].iloc[0]
        named = rows[rows["model"] == c.NAMED_LINE].iloc[0]
        others = rows[~rows["model"].isin(["vendor", c.NAMED_LINE])]
        lines.append(
            f"| {_pct(rate, 0)} | vendor | {_pct(vendor.bad_rate, 2)} | {_millions(vendor.expected_loss)} | - | - |"
        )
        lines.append(
            f"| {_pct(rate, 0)} | scorecard | {_pct(named.bad_rate, 2)} | {_millions(named.expected_loss)} | "
            f"{int(named.defaults_avoided_vs_vendor):+,} | {_signed_millions(named.expected_loss_delta_vs_vendor)} "
            f"({_signed_pct(named.expected_loss_pct_change_vs_vendor)}) |"
        )
        lines.append(
            f"| {_pct(rate, 0)} | other six lines | {_pct(others.bad_rate.min(), 2)} to {_pct(others.bad_rate.max(), 2)} | "
            f"{_millions(others.expected_loss.min())} to {_millions(others.expected_loss.max())} | "
            f"{int(others.defaults_avoided_vs_vendor.min()):+,} to {int(others.defaults_avoided_vs_vendor.max()):+,} | "
            f"{_signed_pct(others.expected_loss_pct_change_vs_vendor.min())} to "
            f"{_signed_pct(others.expected_loss_pct_change_vs_vendor.max())} |"
        )
    lines.append("")
    return lines


def build(tables: dict[str, pd.DataFrame], frame: pd.DataFrame) -> str:
    regime = c.HEADLINE_REGIME

    def headline(name: str) -> pd.DataFrame:
        table = tables[name]
        return table[table["regime"] == regime].reset_index(drop=True)

    lines = [
        "# Champion and challenger decision report",
        "",
        "This report compares a simulated vendor score with in-house challenger models on a synthetic Philippine "
        "behavioural panel. The vendor is a simulation built for this testbed and the panel is generated data. "
        "Nothing here says how any real vendor or any real borrower population would behave.",
        "",
        f"Every number is measured on the held-out applicants at month {c.CHECKPOINT} ({len(frame):,} applicants, "
        f"{int(frame['bad_6m'].sum()):,} bad on the 6-month outcome) in the `{regime}` regime, where the data "
        "owner keeps the repayment outcomes. The same tables for the `vendor_only` regime are in the CSV files. "
        f"The named challenger is the in-house scorecard. Expected loss is the bad outcome times the loan amount "
        f"times an assumed loss-given-default of {_pct(c.LOSS_GIVEN_DEFAULT, 0)}; that 60% is an assumption, "
        "not a measurement. Loan amounts are in the panel's own currency units.",
        "",
        *_lift_section(headline("lift_by_group.csv")),
        *_switch_section(headline("phased_switch.csv")),
        *_swap_section(headline("swap_sets.csv")),
        *_equal_section(headline("equal_approval.csv")),
        "## How to read this",
        "",
        "Results are reported as they came out. Where the scorecard or another challenger does worse than the "
        "vendor, that is the finding. AUC alone is not the decision; the approval-rate, default and loss tables "
        "are. This report makes no claim that the in-house model is better than any real vendor.",
        "",
        "Files: `lift_by_group.csv`, `phased_switch.csv`, `swap_sets.csv`, `equal_approval.csv`, `full_lines.csv`.",
        "",
    ]
    return "\n".join(lines)

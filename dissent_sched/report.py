"""Markdown reports for the pathway audit and the schedule search."""


def audit_report_markdown(scenario, diagnosis):
    lines = []
    lines.append("# Failure-pathway audit: %s" % scenario.name)
    lines.append("")
    lines.append(
        "Free debate over %d calibration cases: %d correct finals, %d "
        "failures, of which %d had no privately correct agent (absent "
        "-- no debate policy can rescue those)."
        % (
            diagnosis["n_cases"],
            diagnosis["n_correct_final"],
            diagnosis["n_failed"],
            diagnosis["n_absent"],
        )
    )
    lines.append("")
    lines.append("| pathway | failures | share of attributable |")
    lines.append("|---|---|---|")
    for pathway in (
        "sycophantic_conformity", "fragility", "consensus_collapse"
    ):
        lines.append(
            "| %s | %d | %.1f%% |"
            % (
                pathway,
                diagnosis["pathway_counts"][pathway],
                diagnosis["pathway_shares"][pathway] * 100.0,
            )
        )
    lines.append("")
    drivers = diagnosis["collapse_drivers"]
    lines.append(
        "Consensus-collapse cases were driven by conformity in %d "
        "cases and by fragility in %d."
        % (drivers["conformity"], drivers["fragility"])
    )
    lines.append("")
    if diagnosis["dominant_pathway"] is not None:
        lines.append(
            "**Dominant pathway: %s -> recommended dissent mode: %s.**"
            % (
                diagnosis["dominant_pathway"],
                diagnosis["recommended_mode"],
            )
        )
    else:
        lines.append(
            "**No attributable failures: no dissent mode is recommended.**"
        )
    lines.append("")
    return "\n".join(lines)


def schedule_report_markdown(scenario, search, diagnosis=None):
    lines = []
    lines.append("# Dissent schedule search: %s" % scenario.name)
    lines.append("")
    if diagnosis is not None:
        lines.append(
            "Pathway audit on the calibration cases: dominant pathway "
            "%s (recommended mode %s)."
            % (
                diagnosis["dominant_pathway"],
                diagnosis["recommended_mode"],
            )
        )
        lines.append("")
    best = search["best"]
    lines.append(
        "Searched %d schedules on %d calibration cases (%d rounds). "
        "Ranking: oracle-gap closure per 1k tokens."
        % (
            len(search["table"]),
            search["n_calibration"],
            search["rounds"],
        )
    )
    lines.append("")
    lines.append(
        "**Chosen schedule: %s** -- accuracy %.3f, gap closure %.3f, "
        "%.4f closure per 1k tokens at %.0f tokens per case."
        % (
            best["key"],
            best["accuracy"],
            best["gap_closure"],
            best["closure_per_1k_tokens"],
            best["mean_tokens"],
        )
    )
    by_acc = search["best_by_accuracy"]
    lines.append(
        "Best by raw accuracy: %s -- accuracy %.3f at %.0f tokens per "
        "case (%.4f closure per 1k tokens)."
        % (
            by_acc["key"],
            by_acc["accuracy"],
            by_acc["mean_tokens"],
            by_acc["closure_per_1k_tokens"],
        )
    )
    lines.append("")
    lines.append(
        "| rank | schedule | accuracy | gap closure | closure / 1k "
        "tokens | tokens / case | dissent events / case |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for rank, row in enumerate(search["table"][:10], start=1):
        lines.append(
            "| %d | %s | %.3f | %.3f | %.4f | %.0f | %.2f |"
            % (
                rank,
                row["key"],
                row["accuracy"],
                row["gap_closure"],
                row["closure_per_1k_tokens"],
                row["mean_tokens"],
                row["mean_dissent_events"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def policy_report_markdown(scenario, rows):
    """Compact policy comparison table for one scenario."""
    lines = []
    lines.append("## Policy comparison: %s (held-out cases)" % scenario.name)
    lines.append("")
    lines.append(
        "| policy | accuracy | tokens / case | gap closure | closure "
        "/ 1k tokens |"
    )
    lines.append("|---|---|---|---|---|")
    for row in rows:
        lines.append(
            "| %s | %.3f | %.0f | %.3f | %.4f |"
            % (
                row["policy"],
                row["accuracy"],
                row["mean_tokens"],
                row["gap_closure"],
                row["closure_per_1k_tokens"],
            )
        )
    lines.append("")
    return "\n".join(lines)

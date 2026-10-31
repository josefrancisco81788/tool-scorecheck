import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from scorecheck import config, features, models, panel, vendor

DATA_ROOT = Path("data/processed")
STAGES: tuple[str, ...] = ("vendor", "models", "experiment", "report", "validate", "explain")


@dataclass(frozen=True)
class RunRequest:
    scale: str
    n_households: int


def parse_args(argv: Sequence[str] | None) -> RunRequest:
    parser = argparse.ArgumentParser(
        prog="python -m scorecheck",
        description=(
            "Generate the synthetic panel, publish the vendor ledger, and record in-house "
            "challengers in shadow mode."
        ),
    )
    parser.add_argument("--scale", choices=sorted(config.SCALES), default="default")
    args = parser.parse_args(argv)
    return RunRequest(scale=args.scale, n_households=config.SCALES[args.scale])


def main(argv: Sequence[str] | None = None) -> int:
    request = parse_args(argv)
    print(config.BANNERS[request.scale], flush=True)
    run_dir = panel.generate(config.SEED, request.n_households, DATA_ROOT)
    features.from_panel(run_dir)
    vendor.publish(run_dir)
    models.publish(run_dir)
    for stage in STAGES:
        print(stage)
    return 0

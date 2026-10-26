import numpy as np
import pandas as pd
import pytest

from scorecheck.logical_hash import LogicalHashError, logical_bytes, logical_hash

WORKED_DIGEST = "492c75a4c990cada69f18ffcaabb27d2e53edd18a5ddf87e19491ba7aba584b2"
WORKED_BYTES = (
    "person_id,region,shared,wallet_inflow\n"
    "1,NCR,1,0.500000\n"
    '1,"Region VII, Cebu",0,<NA>\n'
    "2,NCR,1,1500.123457\n"
).encode("utf-8")


def worked_example() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": ["NCR", "Region VII, Cebu", "NCR"],
            "person_id": np.array([2, 1, 1], dtype=np.int64),
            "wallet_inflow": [1500.1234567, np.nan, 0.5],
            "shared": [True, False, True],
        }
    )


def test_worked_example_bytes_and_digest():
    frame = worked_example()
    assert logical_bytes(frame) == WORKED_BYTES
    assert logical_hash(frame) == WORKED_DIGEST


def test_worked_example_any_order():
    frame = worked_example().sample(frac=1.0, random_state=3)[["shared", "wallet_inflow", "region", "person_id"]]
    assert logical_hash(frame.reset_index(drop=True)) == WORKED_DIGEST


def test_negative_zero_and_quotes():
    frame = pd.DataFrame(
        {"person_id": np.array([1, 2], dtype=np.int64), "x": [-0.0000001, 2.0], "region": ['say "hi"', "a\nb"]}
    )
    assert logical_bytes(frame) == (
        'person_id,region,x\n1,"say ""hi""",0.000000\n2,"a\nb",2.000000\n'
    ).encode("utf-8")


@pytest.mark.parametrize(
    "frame",
    [
        pd.DataFrame({"person_id": [1.0, 2.0]}),
        pd.DataFrame({"person_id": pd.array([1, None], dtype="Int64")}),
        pd.DataFrame({"person_id": np.array([1, 2], dtype=np.int64), "month": [1.0, 2.5]}),
        pd.DataFrame({"person_id": np.array([1, 2], dtype=np.int64), "month": [1.0, np.nan]}),
    ],
    ids=["float-id", "null-id", "non-whole-int-column", "null-int-column"],
)
def test_no_digest_for_bad_int_columns(frame):
    with pytest.raises(LogicalHashError):
        logical_hash(frame)

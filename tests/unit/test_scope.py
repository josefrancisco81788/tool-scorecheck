import re

from support.runs import ALL_TABLE_NAMES

FIRM_WORDS = re.compile("firm|msme|business|enterprise|company", re.IGNORECASE)


def test_no_firm_entities(run_300):
    names = list(ALL_TABLE_NAMES)
    for table in ALL_TABLE_NAMES:
        names.extend(run_300[table].columns)
    names.extend(run_300["person"]["role"].unique())
    assert [n for n in names if FIRM_WORDS.search(str(n))] == []

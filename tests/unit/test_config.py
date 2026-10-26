from scorecheck import config

ALLOWED_SOURCES = {"BSP", "telco", "Meralco", "assumption"}


def _all_sourced_in_config():
    found = []
    for value in vars(config).values():
        if isinstance(value, config.Sourced):
            found.append(value)
        elif isinstance(value, dict):
            found.extend(v for v in value.values() if isinstance(v, config.Sourced))
    return found


def test_scale_constants():
    assert isinstance(config.SEED, int) and not isinstance(config.SEED, bool)
    assert config.SCALE_DEFAULT == 50000
    assert config.SCALE_FULL == 200000
    assert config.N_MONTHS == 24


def test_banner_text():
    assert config.BANNERS["default"] == (
        "This run uses the default scale of 50,000 households. The full run is 200,000 households."
    )
    assert config.BANNERS["full"] == (
        "This run uses the full scale of 200,000 households. The default run is 50,000 households."
    )


def test_multiplier_sources():
    multipliers = config.generator_multipliers()
    expected_names = (
        {"prepaid_probability", "disconnection_share"}
        | {f"remittance_{m:02d}" for m in range(1, 13)}
    )
    assert set(multipliers) == expected_names
    assert all(m.source in ALLOWED_SOURCES for m in multipliers.values())
    assert sorted(map(id, _all_sourced_in_config())) == sorted(map(id, multipliers.values()))


def test_sourced_rejects_unknown_label():
    try:
        config.Sourced(1.0, "guess")
    except ValueError:
        return
    raise AssertionError("Sourced accepted a label outside the four sources")


def test_prepaid_config():
    assert config.PREPAID_PROBABILITY.value == 0.96
    assert config.PREPAID_PROBABILITY.source == "telco"


def test_remittance_config():
    rem = config.REMITTANCE_MULTIPLIERS
    assert sorted(rem) == list(range(1, 13))
    for month, value in ((4, 0.90), (5, 0.90), (7, 1.07), (12, 1.18)):
        assert rem[month].value == value
        assert rem[month].source == "BSP"


def test_disconnection_config():
    assert config.DISCONNECTION_SHARE.value == 0.05
    assert config.DISCONNECTION_SHARE.source == "assumption"


def test_driver_weights_nonzero_in_config():
    assert config.ability_default_weight != 0
    assert config.willingness_default_weight != 0


def test_scale_name():
    assert config.scale_name(config.SCALE_DEFAULT) == "default"
    assert config.scale_name(config.SCALE_FULL) == "full"
    assert config.scale_name(300) == "custom"

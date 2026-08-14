import sys, types, importlib.util, pathlib
import pytest
from unittest.mock import MagicMock, patch
from datetime import time

pd = pytest.importorskip('pandas')

arm = pathlib.Path(__file__).resolve().parents[1]
# `utils/validation.py` does `from config import ...` and
# `from aqualog_db.repositories import ...`, so the project arm must be importable.
if str(arm) not in sys.path:
    sys.path.insert(0, str(arm))

# Stub streamlit for modules that expect it
st = types.ModuleType('streamlit')
st.session_state = {}
sys.modules['streamlit'] = st

# validation.py also uses the relative import `from .chemistry import nh3_fraction`,
# which only resolves if the module is loaded under a package-qualified name.
# Register a lightweight `utils` package (rather than importing the real
# `utils/__init__.py`, which pulls in the whole Streamlit UI layer) so the
# relative import resolves against utils/ on disk.
if 'utils' not in sys.modules:
    utils_pkg = types.ModuleType('utils')
    utils_pkg.__path__ = [str(arm / 'utils')]
    sys.modules['utils'] = utils_pkg

module_path = arm / 'utils' / 'validation.py'
spec = importlib.util.spec_from_file_location('utils.validation', module_path)
validation = importlib.util.module_from_spec(spec)
sys.modules['utils.validation'] = validation
spec.loader.exec_module(validation)

arrow_safe = validation.arrow_safe
is_too_low = validation.is_too_low
is_too_high = validation.is_too_high
is_out_of_range = validation.is_out_of_range


def test_arrow_safe_converts_date():
    df = pd.DataFrame({'date': ['2024-01-01', '2024-01-02']})
    out = arrow_safe(df)
    # The exact resolution is pandas' choice ([ns] on pandas 2, [us] on pandas 3);
    # arrow_safe only guarantees the column is a datetime dtype.
    assert pd.api.types.is_datetime64_any_dtype(out['date'])


def test_threshold_helpers():
    assert is_too_low('nitrate', 10.0)
    assert not is_too_low('nitrate', 20.0)
    assert is_too_high('ph', 8.5)
    assert not is_too_high('ph', 8.0)
    assert not is_too_high('unknown', 1.0)


# ── is_out_of_range ────────────────────────────────────────────────────────────

def _mock_repos(custom_range=None, has_co2=True, co2_on=9, co2_off=17):
    """Return a context that patches CustomRangeRepository and TankRepository."""
    custom_repo = MagicMock()
    custom_repo.get.return_value = custom_range
    tank_repo = MagicMock()
    tank_repo.get_by_id.return_value = {
        "has_co2": has_co2,
        "co2_on_hour": co2_on,
        "co2_off_hour": co2_off,
    }
    return custom_repo, tank_repo


def test_oor_ph_in_range():
    custom_repo, tank_repo = _mock_repos()
    with patch.object(validation, 'CustomRangeRepository', return_value=custom_repo), \
         patch.object(validation, 'TankRepository', return_value=tank_repo):
        assert not is_out_of_range('ph', 7.0, tank_id=1)


def test_oor_ph_too_high():
    custom_repo, tank_repo = _mock_repos()
    with patch.object(validation, 'CustomRangeRepository', return_value=custom_repo), \
         patch.object(validation, 'TankRepository', return_value=tank_repo):
        assert is_out_of_range('ph', 9.0, tank_id=1)


def test_oor_ph_too_low():
    custom_repo, tank_repo = _mock_repos()
    with patch.object(validation, 'CustomRangeRepository', return_value=custom_repo), \
         patch.object(validation, 'TankRepository', return_value=tank_repo):
        assert is_out_of_range('ph', 5.0, tank_id=1)


def test_oor_ammonia_safe_unionized():
    """Total ammonia of 0.5 ppm at low pH/temp produces negligible NH3 — not flagged."""
    custom_repo, tank_repo = _mock_repos()
    with patch.object(validation, 'CustomRangeRepository', return_value=custom_repo), \
         patch.object(validation, 'TankRepository', return_value=tank_repo):
        result = is_out_of_range('ammonia', 0.5, tank_id=1, ph=6.5, temp_c=20.0)
        assert not result


def test_oor_ammonia_toxic_unionized():
    """High pH + high temp + moderate ammonia → toxic NH3 fraction > 0.02."""
    custom_repo, tank_repo = _mock_repos()
    with patch.object(validation, 'CustomRangeRepository', return_value=custom_repo), \
         patch.object(validation, 'TankRepository', return_value=tank_repo):
        result = is_out_of_range('ammonia', 2.0, tank_id=1, ph=8.5, temp_c=30.0)
        assert result


def test_oor_co2_green_not_flagged():
    custom_repo, tank_repo = _mock_repos()
    with patch.object(validation, 'CustomRangeRepository', return_value=custom_repo), \
         patch.object(validation, 'TankRepository', return_value=tank_repo):
        assert not is_out_of_range('co2_indicator', 'Green', tank_id=1)


def test_oor_co2_yellow_always_flagged():
    custom_repo, tank_repo = _mock_repos()
    with patch.object(validation, 'CustomRangeRepository', return_value=custom_repo), \
         patch.object(validation, 'TankRepository', return_value=tank_repo):
        assert is_out_of_range('co2_indicator', 'Yellow', tank_id=1)


def test_oor_co2_blue_during_on_period_flagged():
    """Blue CO2 during the injection window (e.g. 11 AM) should be flagged."""
    custom_repo, tank_repo = _mock_repos(co2_on=9, co2_off=17)
    with patch.object(validation, 'CustomRangeRepository', return_value=custom_repo), \
         patch.object(validation, 'TankRepository', return_value=tank_repo):
        result = is_out_of_range('co2_indicator', 'Blue', tank_id=1, test_time=time(11, 0))
        assert result


def test_oor_co2_blue_outside_on_period_suppressed():
    """Blue CO2 outside the injection window (e.g. 3 AM) should be suppressed."""
    custom_repo, tank_repo = _mock_repos(co2_on=9, co2_off=17)
    with patch.object(validation, 'CustomRangeRepository', return_value=custom_repo), \
         patch.object(validation, 'TankRepository', return_value=tank_repo):
        result = is_out_of_range('co2_indicator', 'Blue', tank_id=1, test_time=time(3, 0))
        assert not result


def test_oor_co2_no_co2_tank_not_flagged():
    """Tanks without CO2 should never trigger a co2_indicator warning."""
    custom_repo, tank_repo = _mock_repos(has_co2=False)
    with patch.object(validation, 'CustomRangeRepository', return_value=custom_repo), \
         patch.object(validation, 'TankRepository', return_value=tank_repo):
        assert not is_out_of_range('co2_indicator', 'Blue', tank_id=1)


def test_oor_custom_range_overrides_global():
    """A custom range of (5.0, 6.0) for pH should flag a value of 7.0."""
    custom_repo, tank_repo = _mock_repos(custom_range=(5.0, 6.0))
    with patch.object(validation, 'CustomRangeRepository', return_value=custom_repo), \
         patch.object(validation, 'TankRepository', return_value=tank_repo):
        assert is_out_of_range('ph', 7.0, tank_id=1)


def test_oor_unknown_param_returns_false():
    custom_repo, tank_repo = _mock_repos(custom_range=None)
    with patch.object(validation, 'CustomRangeRepository', return_value=custom_repo), \
         patch.object(validation, 'TankRepository', return_value=tank_repo):
        assert not is_out_of_range('unknown_param', 999.0, tank_id=1)

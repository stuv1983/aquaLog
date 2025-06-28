import sys, types, importlib.util, pathlib
import pytest

pd = pytest.importorskip('pandas')

# Stub streamlit for modules that expect it
st = types.ModuleType('streamlit')
st.session_state = {}
sys.modules['streamlit'] = st

module_path = pathlib.Path(__file__).resolve().parents[1] / 'utils' / 'validation.py'
spec = importlib.util.spec_from_file_location('validation', module_path)
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)

arrow_safe = validation.arrow_safe
is_too_low = validation.is_too_low
is_too_high = validation.is_too_high


def test_arrow_safe_converts_date():
    df = pd.DataFrame({'date': ['2024-01-01', '2024-01-02']})
    out = arrow_safe(df)
    assert str(out['date'].dtype) == 'datetime64[ns]'


def test_threshold_helpers():
    assert is_too_low('nitrate', 10.0)
    assert not is_too_low('nitrate', 20.0)
    assert is_too_high('ph', 8.5)
    assert not is_too_high('ph', 8.0)
    assert not is_too_high('unknown', 1.0)

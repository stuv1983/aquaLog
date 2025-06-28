import sys, types, importlib.util, pathlib

# Provide a minimal stub for streamlit
st = types.ModuleType('streamlit')
st.session_state = {'units': 'Metric'}
sys.modules['streamlit'] = st

module_path = pathlib.Path(__file__).resolve().parents[1] / 'utils' / 'localization.py'
spec = importlib.util.spec_from_file_location('localization', module_path)
localization = importlib.util.module_from_spec(spec)
spec.loader.exec_module(localization)

convert_value = localization.convert_value
format_with_units = localization.format_with_units


def test_temperature_conversion():
    st.session_state['units'] = 'Imperial'
    assert convert_value(0.0, 'temperature') == 32.0
    st.session_state['units'] = 'Metric'
    assert convert_value(0.0, 'temperature') == 0.0


def test_format_with_units():
    st.session_state['units'] = 'Metric'
    assert format_with_units(25.0, 'temperature') == '25.0 \u00b0C'
    st.session_state['units'] = 'Imperial'
    assert format_with_units(25.0, 'temperature') == '77.0 \u00b0F'
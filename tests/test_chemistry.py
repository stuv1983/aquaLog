import sys, types, math, importlib.util, pathlib

# Stub streamlit to avoid dependency
st = types.ModuleType('streamlit')
st.session_state = {}
sys.modules['streamlit'] = st

module_path = pathlib.Path(__file__).resolve().parents[1] / 'utils' / 'chemistry.py'
spec = importlib.util.spec_from_file_location('chemistry', module_path)
chemistry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chemistry)

nh3_fraction = chemistry.nh3_fraction
calculate_alkaline_buffer_dose = chemistry.calculate_alkaline_buffer_dose
calculate_equilibrium_dose = chemistry.calculate_equilibrium_dose
calculate_fritzzyme7_dose = chemistry.calculate_fritzzyme7_dose
calculate_volume = chemistry.calculate_volume
calculate_water_change_percentage = chemistry.calculate_water_change_percentage


def test_nh3_fraction():
    result = nh3_fraction(1.0, 8.0, 25.0)
    assert math.isclose(result, 0.0537, rel_tol=1e-3)


def test_alkaline_buffer_dose():
    grams = calculate_alkaline_buffer_dose(100.0, 2.0)
    assert math.isclose(grams, 5.357, rel_tol=1e-3)


def test_equilibrium_dose():
    grams = calculate_equilibrium_dose(100.0, 2.0)
    assert math.isclose(grams, 13.333, rel_tol=1e-3)


def test_fritzzyme7_dose_new():
    ml, oz = calculate_fritzzyme7_dose(76.0, is_new_system=True)
    assert math.isclose(ml, 238.0, rel_tol=1e-3)
    assert math.isclose(oz, 8.0477, rel_tol=1e-3)


def test_volume_calculation_cm():
    liters, gallons = calculate_volume(100.0, 50.0, 40.0, 'cm')
    assert math.isclose(liters, 200.0, rel_tol=1e-3)
    assert math.isclose(gallons, 52.834, rel_tol=1e-3)


def test_volume_calculation_inches():
    liters, gallons = calculate_volume(20.0, 10.0, 12.0, 'inches')
    assert math.isclose(liters, 39.329, rel_tol=1e-3)
    assert math.isclose(gallons, 10.391, rel_tol=1e-3)


def test_volume_calculation_invalid():
    liters, gallons = calculate_volume(1.0, 1.0, 1.0, 'feet')
    assert liters == 0.0 and gallons == 0.0


def test_water_change_percentage():
    pct = calculate_water_change_percentage(100.0, 50.0)
    assert math.isclose(pct, 50.0, rel_tol=1e-3)
    pct = calculate_water_change_percentage(50.0, 60.0)
    assert pct == 0.0

# utils/chemistry.py

"""
chemistry.py – Aquarium Chemistry Calculations

Contains all chemistry-related calculation functions for AquaLog. Includes logic
for calculating the toxic unionized ammonia (NH₃) fraction and various dosing
recommendations for common aquarium supplements. It also provides a utility
for calculating aquarium volumes.
"""

from __future__ import annotations # Added for type hinting consistency

from typing import Optional

def nh3_fraction(total_amm: float, ph: float, temp_c: float) -> float:
    """
    Calculates the fraction of highly toxic unionized ammonia (NH₃) from
    total ammonia (NH₃ + NH₄⁺) based on water pH and temperature.

    This calculation is crucial because only unionized ammonia is toxic to fish,
    and its proportion varies significantly with pH and temperature.

    Args:
        total_amm (float): The total ammonia concentration in ppm (parts per million).
        ph (float): The current pH value of the water.
        temp_c (float): The temperature of the water in Celsius.

    Returns:
        float: The calculated concentration of unionized NH₃ in ppm.
               This is `total_ammonia * fraction_of_unionized_ammonia`.
    """
    # pKa (acid dissociation constant) for ammonia is temperature-dependent.
    # This formula is an approximation for typical aquarium temperatures.
    pka = 0.09018 + 2729.92 / (273.15 + temp_c)
    
    # Calculate the fraction of unionized ammonia (NH3) using the Henderson-Hasselbalch equation.
    # The higher the pH and temperature, the greater the fraction of toxic NH3.
    frac = 1 / (1 + 10 ** (pka - ph))
    
    return total_amm * frac

def calculate_alkaline_buffer_dose(volume_l: float, delta_kh: float) -> float:
    """
    Calculates the recommended dosage (in grams) of Seachem Alkaline Buffer
    needed to raise the Carbonate Hardness (KH) in an aquarium.

    The calculation is based on typical product instructions where approximately
    1 teaspoon (6 grams) of Seachem Alkaline Buffer raises KH by 2.8 dKH in 80 liters.

    Args:
        volume_l (float): The volume of the tank in liters.
        delta_kh (float): The desired increase in KH, in dKH (degrees of Carbonate Hardness).
                          For example, if current KH is 2 and target is 4, delta_kh would be 2.

    Returns:
        float: The calculated amount of Seachem Equilibrium needed in grams.
    """
    # The factor 1 / (80 * 2.8) represents tsp/L/dKH based on product claims.
    # 80 L is the volume, 2.8 dKH is the rise per 1 teaspoon.
    tsp_per_l_per_dkh = 1 / (80 * 2.8)  # ~0.004464 tsp per liter per dKH
    grams_per_tsp = 6 # Approximately 6 grams per teaspoon of Alkaline Buffer
    
    # Calculate total grams needed: (volume * desired_change_dKH * conversion_factor)
    return volume_l * delta_kh * tsp_per_l_per_dkh * grams_per_tsp # Corrected variable name

def calculate_equilibrium_dose(volume_l: float, delta_gh: float) -> float:
    """
    Calculates the recommended dosage (in grams) of Seachem Equilibrium
    needed to raise the General Hardness (GH) in an aquarium.

    The calculation is based on typical product instructions where 16 grams
    of Seachem Equilibrium raises GH by 3 dGH in 80 liters.

    Args:
        volume_l (float): The volume of the tank in liters.
        delta_gh (float): The desired increase in GH, in dGH (degrees of General Hardness).
                          For example, if current GH is 4 and target is 6, delta_gh would be 2.

    Returns:
        float: The calculated amount of Seachem Equilibrium needed in grams.
    """
    # The factor 16 / (80 * 3) represents grams/L/dGH based on product claims.
    # 80 L is the volume, 3 dGH is the rise per 16 grams.
    grams_per_l_per_dgh = 16 / (80 * 3)  # ~ 0.0667 grams per liter per dGH
    
    # Calculate total grams needed: (volume * desired_change_dKH * conversion_factor)
    return volume_l * delta_gh * grams_per_l_per_dgh

def calculate_fritzzyme7_dose(volume_l: float, is_new_system: bool = True) -> tuple[float, float]:
    """
    Calculates the recommended dose of FritzZyme 7 nitrifying bacteria solution
    based on tank volume and whether it's a new or established system.

    Dosage rates differ for new (cycling) versus established (maintenance/rescue) systems.
    These rates are based on typical product recommendations (e.g., 119ml per 38L for new systems).

    Args:
        volume_l (float): The volume of the tank in liters.
        is_new_system (bool): A boolean. True for new system dosage (higher dose),
                              False for established system dosage (lower dose).

    Returns:
        tuple[float, float]: A tuple containing the calculated dose in (milliliters, fluid ounces).
    """
    if is_new_system:
        # New systems: 119 ml per 38 L (approx. 10 US Gallons)
        dose_ml = (volume_l / 38.0) * 119.0
    else:
        # Established systems: 60 ml per 38 L (approx. 10 US Gallons)
        dose_ml = (volume_l / 38.0) * 60.0
    
    # Convert milliliters to fluid ounces (1 fl oz ≈ 29.5735 ml)
    dose_oz = dose_ml / 29.5735
    
    return dose_ml, dose_oz

def calculate_volume(length: float, width: float, height: float, units: str) -> tuple[float, float]:
    """
    Calculates the volume of a rectangular aquarium tank in liters and US gallons.

    Args:
        length (float): The length of the tank.
        width (float): The width of the tank.
        height (float): The height of the tank.
        units (str): The units of the input dimensions ('cm' or 'inches').

    Returns:
        tuple[float, float]: A tuple containing the volume in (liters, gallons).
                             Returns `(0.0, 0.0)` if an unsupported unit is provided.
    """
    if units == 'cm':
        # Volume in cubic centimeters, then convert to liters (1000 cm³ = 1 L)
        volume_liters = (length * width * height) / 1000
    elif units == 'inches':
        # Volume in cubic inches, then convert to liters (1 cubic inch ≈ 0.0163871 L)
        volume_liters = (length * width * height) * 0.0163871
    else:
        # Return zeros for unsupported units
        return 0.0, 0.0
        
    # Convert liters to US gallons (1 US gallon ≈ 3.78541 liters, so 1 L ≈ 0.264172 US gallons)
    volume_gallons = volume_liters * 0.264172
    return volume_liters, volume_gallons

def calculate_water_change_percentage(current_value: float, target_value: float) -> float:
    """
    Calculates the percentage of water to change to reduce a specific parameter
    from its current value to a target value.

    Args:
        current_value (float): The current concentration of the parameter.
        target_value (float): The desired concentration of the parameter.

    Returns:
        float: The calculated water change percentage (0-100%).
               Returns `0.0` if `current_value` is not positive, or if `target_value`
               is greater than or equal to `current_value` (indicating no reduction needed).
    """
    if current_value <= 0:
        return 0.0 # Cannot calculate if current value is zero or negative

    if target_value >= current_value:
        return 0.0 # No reduction needed or possible

    # Calculate reduction factor, then percentage
    reduction_factor = (current_value - target_value) / current_value
    return reduction_factor * 100
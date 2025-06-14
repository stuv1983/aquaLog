from typing import Optional

def nh3_fraction(total_amm: float, ph: float, temp_c: float) -> float:
    """
    Calculates unionized NH₃ from total ammonia based on pH & temperature.
    
    Args:
        total_amm: Total ammonia concentration
        ph: Current pH
        temp_c: Temperature in Celsius
        
    Returns:
        Fraction of unionized NH₃
    """
    pka = 0.09018 + 2729.92 / (273.15 + temp_c)
    frac = 1 / (1 + 10 ** (pka - ph))
    return total_amm * frac

def calculate_alkaline_buffer_dose(volume_l: float, delta_kh: float) -> float:
    """
    Calculates grams of Seachem Alkaline Buffer needed to raise KH.
    
    Args:
        volume_l: Tank volume in liters
        delta_kh: Desired KH increase in dKH
        
    Returns:
        Grams of buffer needed
    """
    tsp_per_l_per_dkh = 1 / (80 * 2.8)  # ~0.004464 tsp
    grams_per_tsp = 6
    return volume_l * delta_kh * tsp_per_l_per_dkh * grams_per_tsp

def calculate_equilibrium_dose(volume_l: float, delta_gh: float) -> float:
    """
    Calculates grams of Seachem Equilibrium needed to raise GH.
    
    Args:
        volume_l: Tank volume in liters
        delta_gh: Desired GH increase in dGH
        
    Returns:
        Grams of Equilibrium needed
    """
    grams_per_l_per_dgh = 16 / (80 * 3)  # ≈ 0.0667
    return volume_l * delta_gh * grams_per_l_per_dgh

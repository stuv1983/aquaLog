"""
repositories/__init__.py - Expose repository classes
"""
from .tank import TankRepository
from .water_test import WaterTestRepository
from .custom_range import CustomRangeRepository 
from .email_settings import EmailSettingsRepository

__all__ = [
    'TankRepository',
    'WaterTestRepository',
    'CustomRangeRepository',
    'EmailSettingsRepository'
]
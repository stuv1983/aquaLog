"""
repositories/__init__.py - Expose repository classes
"""
from .tank import TankRepository
from .water_test import WaterTestRepository
from aqualog_db.repositories import CustomRangeRepository
from .email_settings import EmailSettingsRepository

__all__ = [
    'TankRepository',
    'WaterTestRepository',
    'CustomRangeRepository',
    'EmailSettingsRepository'
]
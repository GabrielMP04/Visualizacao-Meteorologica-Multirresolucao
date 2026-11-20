import unittest
from pathlib import Path
import numpy as np
from rasterio.transform import from_bounds
from src.state_data import Weather

class StateWeatherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(__file__).resolve().parents[1]/"data/sao-paulo/b2ba068d34c2bc7f011b1367fb9d92a8.grib"
        if not path.exists(): raise unittest.SkipTest("GRIB local ausente")
        cls.weather=Weather(path,from_bounds(-54,-27,-45,-20,33,33),33)

    def test_period_and_missing_precipitation(self):
        w=self.weather
        self.assertEqual(len(w.times),336)
        self.assertEqual(w.labels[-1],"2026-11-14 23:00")
        self.assertTrue(np.isnan(w.frame("Precipitacao",0)).all())
        self.assertTrue(np.isfinite(w.frame("Precipitacao",1)).any())

    def test_temperatures_vary_and_nodata_is_preserved(self):
        a=self.weather.frame("Temperatura",0)
        b=self.weather.frame("Temperatura",12)
        self.assertTrue(np.isnan(a).any())
        self.assertLess(np.nanmax(a),60)
        self.assertFalse(np.allclose(a,b,equal_nan=True))

    def test_cycle_boundary_is_not_daily_accumulation(self):
        w=self.weather
        a=w.records["Precipitacao"][w.times[24]]
        self.assertGreaterEqual(np.nanmin(a),0)
        self.assertLess(np.nanmax(a),50)

import unittest
import pandas as pd
import prod_model


class TestProdModel(unittest.TestCase):
    def test_preprocess_ff_data(self):
        df = pd.DataFrame(
            data={
                "APINumber": [1, 2, None],
                "Purpose": ["Proppant", "Breaker", None],
                "PercentHFJob": [0.05, 0.00001, None],
                "MassIngredient": [1000000, 100, None],
                "TVD": [5, 10000, 100],
                "TotalBaseWaterVolume": [1000000, 100, None],
                "TotalBaseNonWaterVolume": [1000000, 100, None],
            }
        )

        df = prod_model.preprocess_ff_data(df)

        isinstance(df, pd.DataFrame)  # add assertion here

    def test_preprocess_well_data(self):
        df = pd.DataFrame(
            data={
                "API_WellNo": [1, 2, None],
                "Lat": [45.456, 44.8976, None],
                "Long": [-116.45, -118.7654, None],
                "Slant": ["Horizontal", "Vertical", None],
            }
        )

        df = prod_model.preprocess_well_data(df)

        isinstance(df, pd.DataFrame)  # add assertion here


if __name__ == "__main__":
    unittest.main()

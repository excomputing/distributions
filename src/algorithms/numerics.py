"""
Module numerics.py
"""
import logging

import pandas as pd
import numpy as np


class Numerics:
    """
    Notes
    -----

    Calculating quantiles & extrema via graphics processing units
    """

    def __init__(self, frame: pd.DataFrame) -> None:
        """
        
        :param frame: A telemetric device's time series.
        """

        self.__data: pd.DataFrame = frame.copy()
        self.__cuts = np.array([0.10, 0.25, 0.50, 0.75, 0.90])
        self.__rename = {0.1: 'lower_decile', 0.25: 'lower_quartile', 0.5: 'median',
                         0.75: 'upper_quartile', 0.9: 'upper_decile', 'min': 'minimum',
                         'max': 'maximum'}

    def __quantiles(self) -> pd.DataFrame:
        """
        Determines the daily quantiles of a series.
        
        :return:
            A CUDF data frame of quantiles
        """

        # Calculating per sequence date
        blob: pd.DataFrame = self.__data.copy()[['sequence_id', 'date', 'measure']]
        calc: pd.DataFrame = blob.groupby(by=['sequence_id', 'date']).quantile(q=self.__cuts, numeric_only=True)

        # Set sequence_id & date as normal fields
        calc.reset_index(drop=False, inplace=True, col_level=1,
                         level=['sequence_id', 'date'], col_fill='indices')

        # The above addresses 2 of the three index fields created by group by.  Next
        # set the final index field, the field of quantile cuts, as a normal field.
        calc.reset_index(drop=False, inplace=True)

        # Pivot about the field of quantile cuts, named 'index'.
        matrix = calc.pivot(index=['sequence_id', 'date'], columns='index', values='measure')
        matrix.reset_index(drop=False, inplace=True)

        return matrix

    def __extrema(self) -> pd.DataFrame:
        """
        Determines each day's minimum & maximum measurements, per sequence.
        
        :return:
            A CUDF data frame of extrema
        """

        calc: pd.DataFrame = self.__data[['sequence_id', 'date', 'measure']].groupby(
            by=['sequence_id', 'date']).agg(['min', 'max'])

        calc.reset_index(drop=False, inplace=True, col_level=1,
                         level=['sequence_id', 'date'], col_fill='indices')
        matrix = calc.set_axis(labels=calc.columns.get_level_values(level=1), axis=1)

        return matrix

    @staticmethod
    def __epoch(values: pd.Series) -> np.ndarray:
        """
        Adding an epoch field; milliseconds seconds since 1 January 1970.

        :param values:
        :return:
        """

        nanoseconds: pd.Series = pd.to_datetime(values, format='%Y-%m-%d').astype(np.int64)
        milliseconds: pd.Series = (nanoseconds / (10 ** 6)).astype(np.longlong)

        return milliseconds.values

    def exc(self) -> pd.DataFrame:
        """
        
        :return:
        """

        # Quantiles & Extrema
        quantiles: pd.DataFrame = self.__quantiles()
        extrema: pd.DataFrame = self.__extrema()

        # Merge
        numbers = quantiles.copy().merge(extrema.copy(), on=['sequence_id', 'date'], how='inner')

        # Rename fields
        numbers.rename(columns=self.__rename, inplace=True)

        # Append an epoch field
        numbers.loc[:, 'epochmilli'] = self.__epoch(values=numbers['date'])
        logging.log(level=logging.INFO, msg=numbers)

        return numbers

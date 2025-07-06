# utils/anomaly_detection.py

"""
anomaly_detection.py – Anomaly Detection Utilities

Provides functions for detecting anomalies in time-series data using machine
learning models. This is used to identify unusual or unexpected water parameter
readings that may require attention.
"""

from __future__ import annotations
import pandas as pd
from sklearn.ensemble import IsolationForest

def detect_anomalies(df: pd.DataFrame, params: list[str]) -> pd.DataFrame:
    """
    Detects anomalies in a DataFrame using the Isolation Forest algorithm.

    Args:
        df (pd.DataFrame): The input DataFrame with a 'date' column and
                           numeric parameter columns.
        params (list[str]): A list of parameter columns to use for anomaly
                            detection.

    Returns:
        pd.DataFrame: The original DataFrame with an added 'anomaly' column,
                      where -1 indicates an anomaly and 1 indicates a normal
                      data point.
    """
    if df.empty or not params:
        return df

    # Select the relevant columns and drop rows with missing values
    data = df[params].dropna()

    if data.empty:
        return df

    # Initialize and fit the Isolation Forest model
    # The `contamination` parameter is an estimate of the proportion of outliers
    # in the data set. 'auto' is a good starting point.
    model = IsolationForest(contamination='auto', random_state=42)
    predictions = model.fit_predict(data)

    # Add the predictions to the DataFrame
    data['anomaly'] = predictions

    # Merge the anomaly predictions back into the original DataFrame
    df_with_anomalies = df.merge(data[['anomaly']], left_index=True, right_index=True, how='left')
    df_with_anomalies['anomaly'] = df_with_anomalies['anomaly'].fillna(1)  # Assume non-analyzed rows are normal

    return df_with_anomalies
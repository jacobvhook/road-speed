from sklearn.base import BaseEstimator, TransformerMixin
import numpy as np
import pandas as pd


class LogarithmTransfomer(BaseEstimator, TransformerMixin):
    def __init__(self):
        pass

    def fit(self, X, y=None):
        if isinstance(X, pd.DataFrame):
            self.get_feature_names_in_ = X.columns.to_numpy()
        return self

    def transform(self, X):
        return np.log1p(X)

    def get_feature_names_out(self, input_features):
        return np.apply_along_axis(lambda o: "log_" + o, 0, input_features)


class InverseTransformer(BaseEstimator, TransformerMixin):
    def __init__(self):
        pass

    def fit(self, X, y=None):
        if isinstance(X, pd.DataFrame):
            self.get_feature_names_in_ = X.columns.to_numpy()
        return self

    def transform(self, X):
        return 1 / (1 + X)

    def get_feature_names_out(self, input_features):
        return np.apply_along_axis(lambda o: "inv_" + o, 0, input_features)

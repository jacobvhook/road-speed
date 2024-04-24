from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
import numpy as np

DATA_FOLDER = Path("data")


def main():
    collisions_df = pd.read_pickle(DATA_FOLDER / "final_dataset.pkl")

    collisions_train, collisions_test = train_test_split(
        collisions_df,
        test_size=0.2,
        random_state=42,
        stratify=collisions_df["percentile"],
    )

    def make_new_categories(df: pd.DataFrame) -> pd.DataFrame:
        # Categorical Variables
        df["has_bike_lane"] = ~(df["bike_lane"] == "nan")
        df["has_volume_meas"] = ~df["traffic_volume"].isna()
        df["has_parking"] = df["n_parking_meters"] > 0

        # Imputers
        imputer = SimpleImputer(strategy="mean")
        df[["traffic_volumne"]] = imputer.fit_transform(df[["traffic_volume"]])
        mean_imputer = SimpleImputer(strategy="mean", missing_values=0)
        df[["st_width"]] = mean_imputer.fit_transform(df[["st_width"]])
        df["speed_limit"] = df["speed_limit"].fillna(value=25)

        # Street type Classification
        df["is_av"] = (
            (df["post_type"].isin(["AVE", "BLVD"]))
            | (df["pre_type"] == "AVE")
            | (df["st_name"].isin(["BROADWAY", "BOWERY"]))
        )
        df["is_st"] = df["post_type"] == "ST"
        df["is_rd"] = df["post_type"].isin(["RD", "ROAD"])

        # Logarithms
        df["log_trees"] = np.log1p(df["n_trees"])
        df["log_leng"] = np.log1p(df["shape_leng"])
        df["log_width"] = np.log1p(df["st_width"])
        df["log_traffic_volume"] = np.log1p(df["traffic_volume"])

        # Inverse Tree Operations
        df["inv_trees"] = 1 / (1 + df["log_trees"])

        df["leng_per_tree"] = df["log_leng"] / (1 + df["n_trees"])
        df["width_per_tree"] = df["log_width"] / (1 + df["n_trees"])

        return df

    collisions_train = make_new_categories(collisions_train)
    collisions_test = make_new_categories(collisions_test)

    collisions_train.to_pickle(DATA_FOLDER / "final_dataset_train.pkl")
    collisions_test.to_pickle(DATA_FOLDER / "final_dataset_test.pkl")


if __name__ == "__main__":
    main()

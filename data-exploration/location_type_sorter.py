import pandas as pd


def get_off_cross_streets(file_name_no_csv):
    file_path = file_name_no_csv + ".csv"
    off_street_file_path = file_name_no_csv + "_off_street.csv"
    cross_street_file_path = file_name_no_csv + "_cross_street.csv"

    def is_not_white_space(s: str) -> bool:
        if type(s) is not str:
            return
        return not s.isspace()

    df_no_ll_inj = pd.read_csv(file_path)
    df_no_ll_inj = df_no_ll_inj[
        df_no_ll_inj["LATITUDE"].isna()
        & (
            (
                df_no_ll_inj["NUMBER OF PERSONS INJURED"]
                + df_no_ll_inj["NUMBER OF PERSONS KILLED"]
            )
            > 0
        )
    ]

    df_off_street = df_no_ll_inj[
        df_no_ll_inj["OFF STREET NAME"].notna()
        & df_no_ll_inj["OFF STREET NAME"].apply(is_not_white_space)
    ]
    df_off_street.to_csv(off_street_file_path)

    df_cross_street = df_no_ll_inj.drop(df_off_street.index)
    df_cross_street = df_cross_street[
        df_cross_street["CROSS STREET NAME"].notna()
        & df_cross_street["ON STREET NAME"].notna()
    ]
    df_cross_street.to_csv(cross_street_file_path)


def main():
    file_name_no_csv = "data/Motor_Vehicle_Collisions_-_Crashes_20240318"
    get_off_cross_streets(file_name_no_csv)


if __name__ == "__main__":
    main()

import pandas as pd


def load_user_request_data():
    try:
        request_data = pd.read_csv("additiona_tokens.csv", index_col=[0])
    except Exception as e:
        print("no data file found:", e)
        request_data = pd.DataFrame(
            {"token": ["pepe"]}, index=["uniswap_v2", "uniswap_v3"]
        )
    return request_data


def get_additional_tokens(dex):
    data = load_user_request_data()
    to_add = pd.Series(dtype=float)
    if dex in data.index:
        for i in data.loc[dex]:
            j = i + "<>weth"
            to_add.loc[j] = 1e7
    return to_add


def add_tokens(dex, data):
    to_add = get_additional_tokens(dex)
    return data.append(to_add)

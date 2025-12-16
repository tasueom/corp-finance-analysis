"""
머신러닝 서비스 모듈
모델 학습 및 예측 담당
"""
import pandas as pd
import numpy as np
from app import db


def scikit():
    """머신러닝용 데이터 준비"""
    rows = db.get_all_data()
    
    if not rows:
        raise ValueError("저장된 재무 데이터가 없습니다. 먼저 기업 데이터를 저장해주세요.")
    
    df = pd.DataFrame(rows, columns=["corp_name", "account_id", "account_nm", "amount", "year"])
    df = df[df["account_id"].notna()].copy()
    
    if df.empty:
        raise ValueError("계정과목 코드가 있는 데이터가 없습니다.")
    
    TARGET_IDS = [
        "ifrs-full_Assets",
        "ifrs-full_Equity",
        "ifrs-full_Liabilities"
    ]

    COMMON_IDS = [
        "ifrs-full_CashAndCashEquivalents",
        "ifrs-full_Inventories",
        "ifrs-full_PropertyPlantAndEquipment",
        "ifrs-full_IntangibleAssetsAndGoodwill",
        "ifrs-full_CurrentTradeReceivables",
        "ifrs-full_OtherCurrentAssets",
        "ifrs-full_LongtermBorrowings",
        "ifrs-full_CurrentProvisions",
        "ifrs-full_OtherCurrentLiabilities",
        "ifrs-full_DeferredTaxLiabilities",
        "ifrs-full_IssuedCapital",
        "ifrs-full_RetainedEarnings",
        "ifrs-full_SharePremium",
        "ifrs-full_NoncontrollingInterests"
    ]

    target_df = df[df["account_id"].isin(TARGET_IDS)]
    feature_df = df[df["account_id"].isin(COMMON_IDS)]
    
    if target_df.empty:
        raise ValueError("목표 계정 ID(자산총계, 자본총계, 부채총계) 데이터가 없습니다.")
    
    if feature_df.empty:
        raise ValueError("입력 계정 ID 데이터가 없습니다.")

    pivot = feature_df.pivot_table(
        index=["corp_name","year"],
        columns="account_id",
        values="amount",
        aggfunc="sum"
    ).fillna(0).reset_index()
    
    return pivot, target_df


def train_model(pivot, target_df):
    """모델 학습"""
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
    from sklearn.model_selection import train_test_split
    
    target_pivot = target_df.pivot_table(
        index=["corp_name","year"],
        columns="account_id",
        values="amount",
        aggfunc="sum"
    ).reset_index()

    train_df = pd.merge(pivot, target_pivot, on=["corp_name","year"])
    
    if train_df.empty:
        raise ValueError("학습할 데이터가 없습니다. 재무 데이터를 먼저 저장해주세요.")

    COMMON_IDS = [
        "ifrs-full_CashAndCashEquivalents",
        "ifrs-full_Inventories",
        "ifrs-full_PropertyPlantAndEquipment",
        "ifrs-full_IntangibleAssetsAndGoodwill",
        "ifrs-full_CurrentTradeReceivables",
        "ifrs-full_OtherCurrentAssets",
        "ifrs-full_LongtermBorrowings",
        "ifrs-full_CurrentProvisions",
        "ifrs-full_OtherCurrentLiabilities",
        "ifrs-full_DeferredTaxLiabilities",
        "ifrs-full_IssuedCapital",
        "ifrs-full_RetainedEarnings",
        "ifrs-full_SharePremium",
        "ifrs-full_NoncontrollingInterests"
    ]
    
    COMMON_IDS = [cid for cid in COMMON_IDS if cid in train_df.columns]

    TARGET_IDS = [
        "ifrs-full_Assets",
        "ifrs-full_Equity",
        "ifrs-full_Liabilities"
    ]

    missing_feature_ids = [cid for cid in COMMON_IDS if cid not in train_df.columns]
    missing_target_ids = [tid for tid in TARGET_IDS if tid not in train_df.columns]
    
    if missing_feature_ids or missing_target_ids:
        error_msg = "필수 계정 ID가 없습니다. "
        if missing_feature_ids:
            error_msg += f"입력 계정: {', '.join(missing_feature_ids[:3])}{'...' if len(missing_feature_ids) > 3 else ''}. "
        if missing_target_ids:
            error_msg += f"목표 계정: {', '.join(missing_target_ids)}."
        raise ValueError(error_msg)

    X = train_df[COMMON_IDS]
    y = train_df[TARGET_IDS]
    
    if X.isna().any().any() or y.isna().any().any():
        raise ValueError("데이터에 결측값이 있습니다. 모든 계정 ID의 데이터가 필요합니다.")

    if len(X) >= 2:
        if len(X) <= 5:
            test_size = max(1.0 / len(X), 0.2)
        else:
            test_size = 0.2
        
        train_indices = X.index.tolist()
        train_idx, val_idx = train_test_split(
            train_indices, test_size=test_size, random_state=42, shuffle=True
        )
        
        X_train = X.loc[train_idx]
        X_val = X.loc[val_idx]
        y_train = y.loc[train_idx]
        y_val = y.loc[val_idx]
        
        if len(X_train) == 0 or len(X_val) == 0:
            raise ValueError("데이터 분리 실패: 학습 데이터 {}개, 검증 데이터 {}개".format(len(X_train), len(X_val)))
        
        if set(X_train.index) & set(X_val.index):
            raise ValueError("학습 데이터와 검증 데이터가 겹칩니다!")
    else:
        raise ValueError("학습을 위해서는 최소 2개 이상의 데이터가 필요합니다. 현재 데이터 개수: {}".format(len(X)))
    
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_val)
    y_true = y_val
    
    metrics = {}
    target_names = ["자산총계", "자본총계", "부채총계"]
    is_split = len(X) >= 5
    
    for i, target_name in enumerate(target_names):
        y_true_col = y_true.iloc[:, i].values if hasattr(y_true, 'iloc') else y_true[:, i]
        y_pred_col = y_pred[:, i]
        
        r2 = r2_score(y_true_col, y_pred_col)
        
        if r2 > 0.9999:
            diff = np.abs(y_true_col - y_pred_col)
            relative_error = diff / (np.abs(y_true_col) + 1e-10)
            if np.mean(relative_error) < 0.001:
                pass
        
        mse = mean_squared_error(y_true_col, y_pred_col)
        mae = mean_absolute_error(y_true_col, y_pred_col)
        rmse = np.sqrt(mse)
        
        metrics[target_name] = {
            'r2': r2,
            'mse': mse,
            'mae': mae,
            'rmse': rmse
        }
    
    avg_r2 = np.mean([metrics[name]['r2'] for name in target_names])
    avg_rmse = np.mean([metrics[name]['rmse'] for name in target_names])
    avg_mae = np.mean([metrics[name]['mae'] for name in target_names])

    return model, COMMON_IDS, TARGET_IDS, metrics, {
        'avg_r2': avg_r2,
        'avg_rmse': avg_rmse,
        'avg_mae': avg_mae,
        'is_split': is_split,
        'train_size': len(X_train),
        'val_size': len(X_val)
    }


def predict_company(model, pivot, corp_name, COMMON_IDS, TARGET_IDS, target_year=None):
    """기업의 재무 지표를 예측합니다."""
    corp_data = pivot[pivot["corp_name"] == corp_name].copy()
    if corp_data.empty:
        raise ValueError(f"기업 '{corp_name}'의 데이터를 찾을 수 없습니다.")
    
    corp_data = corp_data.sort_values("year")
    latest = corp_data.iloc[-1]
    latest_year = int(latest["year"])
    
    missing_ids = [cid for cid in COMMON_IDS if cid not in pivot.columns]
    if missing_ids:
        error_msg = f"필수 계정 ID가 없습니다: {', '.join(missing_ids[:3])}"
        if len(missing_ids) > 3:
            error_msg += f" 외 {len(missing_ids) - 3}개"
        raise ValueError(error_msg)
    
    X_input_series = latest[COMMON_IDS]
    if X_input_series.isna().any():
        missing_values = [cid for cid in COMMON_IDS if pd.isna(X_input_series[cid])]
        raise ValueError(f"기업 '{corp_name}'의 필수 계정 데이터가 없습니다: {', '.join(missing_values[:3])}")
    
    X_input_base = pd.to_numeric(X_input_series, errors='coerce').values
    if np.isnan(X_input_base).any():
        missing_values = [COMMON_IDS[i] for i in range(len(COMMON_IDS)) if np.isnan(X_input_base[i])]
        raise ValueError(f"기업 '{corp_name}'의 필수 계정 데이터가 없습니다: {', '.join(missing_values[:3])}")
    
    if target_year and target_year > latest_year:
        year_diff = target_year - latest_year
        
        if len(corp_data) >= 2:
            prev_year_data = corp_data.iloc[-2]
            prev_X = pd.to_numeric(prev_year_data[COMMON_IDS], errors='coerce').values
            
            growth_rates = np.where(
                prev_X > 0,
                np.power(X_input_base / prev_X, 1.0 / (latest_year - int(prev_year_data["year"]))) - 1,
                0
            )
            
            X_input_adjusted = X_input_base * np.power(1 + growth_rates, year_diff)
        else:
            X_input_adjusted = X_input_base
    else:
        X_input_adjusted = X_input_base
    
    X_input = X_input_adjusted.reshape(1, -1)
    pred = model.predict(X_input)[0]

    ID_TO_NAME = {
        "ifrs-full_Assets": "자산총계",
        "ifrs-full_Equity": "자본총계",
        "ifrs-full_Liabilities": "부채총계"
    }

    predicted_assets = pred[0]
    predicted_equity = pred[1]
    predicted_liabilities = pred[2]
    
    liabilities_plus_equity = predicted_liabilities + predicted_equity
    
    if abs(predicted_assets - liabilities_plus_equity) > 0.01:
        adjusted_assets = liabilities_plus_equity
    else:
        adjusted_assets = predicted_assets
    
    return {
        ID_TO_NAME[TARGET_IDS[0]]: int(adjusted_assets),
        ID_TO_NAME[TARGET_IDS[1]]: int(predicted_equity),
        ID_TO_NAME[TARGET_IDS[2]]: int(predicted_liabilities),
    }


def validate_prediction_year(year_str, min_year):
    """
    예측 연도 유효성 검사
    
    Args:
        year_str: 검사할 연도 문자열
        min_year: 최소 연도
    
    Returns:
        tuple: (is_valid: bool, year_int: int or None, error_message: str or None)
    """
    from app.utils import validate_year
    return validate_year(year_str, min_year)


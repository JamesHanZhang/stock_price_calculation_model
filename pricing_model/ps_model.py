import pandas as pd
import numpy as np


class PSPredictionModel():
    def __init__(self):
        self.new_column_lists = [

        ]

    def main(self, df):
        df[self.new_column_lists] = df.apply(self.apply_wrapper, axis=1)
        return df

    def process_rows(self, row_df):
        # ---------- 12. 返回结果 ----------
        return pd.Series({
            '机构估值折价': broker_research_repo_discount,
            '机构置信区间': confidence_lv,
            '机构预测的未来一年归母净利润下限': round(repo_PAT_low, 3),
            '机构预测的未来一年归母净利润上限': round(repo_PAT_high, 3),
            '环比增速与历史环比增速的比较': round(sequential_growth_contrast, 4),
            '综合景气度': round(integrated_bustling_rate, 3),
            '预测未来一年的扣非归母净利润': round(predicted_next_year_NPAT, 3),
            '年增长率': round(growth_rate, 4),
            'PEG=0.8时的PE预测值': PE_PEG80,
            'PEG=1时的PE预测值': PE_PEG100,
            'PEG=1.2时的PE预测值': PE_PEG120,
            'PEG=0.8时的股价预测值': share_price_PEG80,
            'PEG=1时的股价预测值': share_price_PEG100,
            'PEG=1.2时的股价预测值': share_price_PEG120,
            '备注': final_remark
        })

    def _return_nan_series(self, discount, conf, low, high, contrast, bustling, remark):
        """辅助函数：返回全NaN的Series（用于模型失效场景）"""
        return pd.Series({
            '机构估值折价': discount,
            '机构置信区间': conf,
            '机构预测的未来一年归母净利润下限': round(low, 3),
            '机构预测的未来一年归母净利润上限': round(high, 3),
            '环比增速与历史环比增速的比较': round(contrast, 4),
            '综合景气度': round(bustling, 3),
            '预测未来一年的扣非归母净利润': np.nan,
            '年增长率': np.nan,
            'PEG=0.8时的PE预测值': np.nan,
            'PEG=1时的PE预测值': np.nan,
            'PEG=1.2时的PE预测值': np.nan,
            'PEG=0.8时的股价预测值': np.nan,
            'PEG=1时的股价预测值': np.nan,
            'PEG=1.2时的股价预测值': np.nan,
            '备注': remark
        })

    def apply_wrapper(self, row_series):
        row_df = row_series.to_frame().T
        return self.process_rows(row_df)
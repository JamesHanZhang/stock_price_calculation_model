import pandas as pd
import numpy as np

class peg_prediction_model():
    def __init__(self):
        self.new_column_lists = [
            '机构估值折价', '机构置信区间', '机构预测的未来一年归母净利润下限', '机构预测的未来一年归母净利润上限',
            '环比增速与历史环比增速的比较', '综合景气度',
            '预测未来一年的扣非归母净利润', '年增长率', 'PEG=0.8时的PE预测值', 'PEG=1时的PE预测值',
            'PEG=1.2时的PE预测值',
            'PEG=0.8时的股价预测值', 'PEG=1时的股价预测值', 'PEG=1.2时的股价预测值', '备注'
        ]

    def main(self, input_dir, input_file, input_sheet, output_dir, output_file, output_sheet):
        df = pd.read_excel(f"{input_dir}\\{input_file}", sheet_name=input_sheet, header=0)
        df[self.new_column_lists] = df.apply(self.apply_wrapper, axis=1)
        df.to_excel(f"{output_dir}\\{output_file}", sheet_name=output_sheet, index=False)

    def process_rows(self, row_df):
        """
        核心处理逻辑（均值回归衰减模型 + 全修正 + 三级增速预警）
        """
        stock_name = row_df["股票名称"].iloc[0]
        # N为非预测值，即实际的repo值；Y为预测值，即仅预估的值
        if_repo_published = row_df["TTM1利润是否为预测值"].iloc[0]
        current_quarter = int(row_df["当前季度"].iloc[0])

        # ---------- 1. 提取历史季度数据 ----------
        quarters_NPAT = []
        years_NPAT = []
        for q in range(12):
            val = row_df[f"TTM{q + 1}扣非归母净利润"].iloc[0]
            quarters_NPAT.append(val)
            if (q + 1) % 4 == 0:
                year_sum = quarters_NPAT[q - 3] + quarters_NPAT[q - 2] + quarters_NPAT[q - 1] + quarters_NPAT[q]
                years_NPAT.append(year_sum)

        # 计算季节性调整因子（若历史年度利润不稳定则使用均匀分布）
        if any(abs(y) < 1e-6 for y in years_NPAT[:3]):
            avg_current_quarter_percentage = 0.25
            avg_lst_quarter_percentage = 0.25
        else:
            avg_current_quarter_percentage = (
                quarters_NPAT[0] / years_NPAT[0] +
                quarters_NPAT[4] / years_NPAT[1] +
                quarters_NPAT[8] / years_NPAT[2]
            ) / 3
            avg_lst_quarter_percentage = (
                quarters_NPAT[1] / years_NPAT[0] +
                quarters_NPAT[5] / years_NPAT[1] +
                quarters_NPAT[9] / years_NPAT[2]
            ) / 3

        adjusted_season_rate = avg_lst_quarter_percentage / avg_current_quarter_percentage if avg_current_quarter_percentage != 0 else 1.0

        # ---------- 2. 均值回归衰减模型（核心） ----------
        # 历史平均环比（过去两年同季度的环比均值，已做季节性调整）
        hist_qoq_1 = quarters_NPAT[4] / quarters_NPAT[5] if quarters_NPAT[5] != 0 else 1.0
        hist_qoq_2 = quarters_NPAT[8] / quarters_NPAT[9] if quarters_NPAT[9] != 0 else 1.0
        hist_mean_qoq = (hist_qoq_1 + hist_qoq_2) / 2 * adjusted_season_rate

        # 当前环比（脉冲高点）
        # 对当前环比同样进行去季节性处理
        raw_qoq = quarters_NPAT[0] / quarters_NPAT[1] if quarters_NPAT[1] != 0 else 1.0
        current_qoq = raw_qoq * adjusted_season_rate

        # 计算加速度（用于输出参考，不参与预测）
        sequential_growth_contrast = current_qoq - hist_mean_qoq

        # 衰减半衰期（从Excel读取，若无则默认1.5）
        decay_T = row_df["增速半衰周期"].iloc[0]
        if pd.isna(decay_T) or decay_T <= 0:
            decay_T = 1.5

        # 逐季预测未来4个季度环比增速（指数衰减回归至历史均值）
        future_qoq = []
        for t in range(1, 5):
            predicted_qoq = current_qoq * np.exp(-t / decay_T) + hist_mean_qoq * (1 - np.exp(-t / decay_T))
            predicted_qoq = max(0.5, min(1.8, predicted_qoq))
            future_qoq.append(predicted_qoq)

        # 推算未来4个季度利润（基数逐季更新）
        future_NPAT_quarters = []
        current_profit = quarters_NPAT[0]
        for qoq in future_qoq:
            next_profit = current_profit * qoq
            future_NPAT_quarters.append(next_profit)
            current_profit = next_profit

        # 未来一年总利润（加速度模型结果）
        next_year_NPAT = sum(future_NPAT_quarters)

        # ---------- 3. 研报数据读取（预处理） ----------
        broker_research_repo_discount = 0.15
        value = row_df["研报数"].iloc[0]
        broker_research_repo_num = int(value) if pd.notna(value) else 0

        if broker_research_repo_num > 0:
            current_year_predicted_PAT = []
            next_year_predicted_PAT = []
            for b in range(broker_research_repo_num):
                current_year_predicted_PAT.append(float(row_df[f"研报{b + 1}的本年度预测归母净利润"].iloc[0]))
                next_year_predicted_PAT.append(float(row_df[f"研报{b + 1}的下一年预测归母净利润"].iloc[0]))

            # 加权平均（当前年剩余季度和明年季度加权）
            repo_mean = (sum(current_year_predicted_PAT) * (4 - current_quarter) / 4 +
                         sum(next_year_predicted_PAT) * current_quarter / 4) / broker_research_repo_num

            repo_PAT_high = repo_mean * (1 + broker_research_repo_discount)
            repo_PAT_low = repo_mean * (1 - broker_research_repo_discount)

            # 计算置信度（变异系数）
            all_vals = current_year_predicted_PAT + next_year_predicted_PAT
            repo_std = np.std(all_vals)
            repo_mean_all = np.mean(all_vals)
            cv = repo_std / repo_mean_all if repo_mean_all != 0 else 0.5
            confidence_lv = max(0.5, min(1.0, 1 - cv))
        else:
            repo_mean = 0
            repo_PAT_high = 0
            repo_PAT_low = 0
            confidence_lv = 1.0

        # ---------- 4. 研报校准（向均值回归）及半年报年化兜底 ----------
        model_NPAT = next_year_NPAT
        no_repo_remark = ""

        if broker_research_repo_num > 0:
            if next_year_NPAT > repo_PAT_high:
                next_year_NPAT = repo_mean * confidence_lv + next_year_NPAT * (1 - confidence_lv)
            elif next_year_NPAT < repo_PAT_low:
                next_year_NPAT = repo_mean * confidence_lv + next_year_NPAT * (1 - confidence_lv)
        else:
            # 研报数为0：使用半年报年化法兜底（保守取较小值）
            if current_quarter >= 2 and len(years_NPAT) >= 3:
                try:
                    h1_0 = quarters_NPAT[0] + quarters_NPAT[1]
                    h1_1 = quarters_NPAT[4] + quarters_NPAT[5]
                    h1_2 = quarters_NPAT[8] + quarters_NPAT[9]
                    h1_list = [h1_0, h1_1, h1_2]
                    year_0 = years_NPAT[0]
                    year_1 = years_NPAT[1]
                    year_2 = years_NPAT[2]
                    ratios = []
                    for h1, year in zip(h1_list, [year_0, year_1, year_2]):
                        if abs(year) > 1e-6:
                            ratios.append(h1 / year)
                    if len(ratios) >= 2:
                        avg_h1_ratio = np.mean(ratios)
                        annualized_by_h1 = h1_0 / avg_h1_ratio if avg_h1_ratio > 0 else np.nan
                        if not np.isnan(annualized_by_h1) and annualized_by_h1 > 0:
                            next_year_NPAT = min(model_NPAT, annualized_by_h1)
                            no_repo_remark = "无研报覆盖，采用半年报年化保守值"
                        else:
                            no_repo_remark = "无研报覆盖，且年化数据无效，沿用模型值"
                    else:
                        no_repo_remark = "无研报覆盖，历史占比数据不足，沿用模型值"
                except Exception:
                    no_repo_remark = "无研报覆盖，计算年化时出现异常，沿用模型值"
            else:
                no_repo_remark = "无研报覆盖，且当前季度<2或历史数据不足，沿用模型值"

        predicted_next_year_NPAT = next_year_NPAT

        # ---------- 5. 计算EPS和增长率 ----------
        total_share_capital = row_df["总股本"].iloc[0]
        if total_share_capital <= 0:
            return self._return_nan_series(broker_research_repo_discount, confidence_lv, repo_PAT_low, repo_PAT_high,
                                           sequential_growth_contrast, 0, remark="总股本异常")

        next_year_EPS = predicted_next_year_NPAT / total_share_capital


        lst_year_NPAT = years_NPAT[0] - quarters_NPAT[0] + quarters_NPAT[4]

        if lst_year_NPAT <= 0:
            return self._return_nan_series(broker_research_repo_discount, confidence_lv, repo_PAT_low, repo_PAT_high,
                                           sequential_growth_contrast, 0, remark="上年利润非正，PEG分母无效")

        growth_rate = (predicted_next_year_NPAT - lst_year_NPAT) / lst_year_NPAT

        # ---------- 6. 处理负增长（硬失效） ----------
        if growth_rate <= 0:
            return self._return_nan_series(broker_research_repo_discount, confidence_lv, repo_PAT_low, repo_PAT_high,
                                           sequential_growth_contrast, 0, remark="负增长/零增长，PEG失效，请用PB或EV/EBITDA")

        # ---------- 7. 三级增速预警与硬失效机制 ----------
        # 硬失效：增速 > 100%（数学失真）
        if growth_rate > 1.0:
            warn_remarks = "增速>100%，PEG数学意义失真（PE>100倍），建议改用DCF或EV/EBITDA"
            if no_repo_remark:
                warn_remarks += "；" + no_repo_remark
            return self._return_nan_series(broker_research_repo_discount, confidence_lv, repo_PAT_low, repo_PAT_high,
                                           sequential_growth_contrast, 0, remark=warn_remarks)

        # 软警告：增速在 50%~100% 之间
        if growth_rate > 0.5:
            ultra_growth_remark = "增速处于50%-100%超高区间，PEG可靠性下降，建议结合FCFF验证"
        else:
            ultra_growth_remark = ""

        # ---------- 8. 季度利润波动率检查 ----------
        recent_4 = quarters_NPAT[0:4]
        mean_4 = np.mean(recent_4)
        std_4 = np.std(recent_4) if len(recent_4) > 1 else 0
        if mean_4 != 0 and std_4 / abs(mean_4) > 0.5:
            volatility_remark = "季度利润波动剧烈（变异系数>0.5），可能存在非经常性损益干扰"
        else:
            volatility_remark = ""

        # ---------- 14. 龙头软警告（仅当股票不是龙头自身） ----------
        # 获取行业龙头名称
        industry_leader_name = row_df.get("行业龙头", [""]).iloc[0] if "行业龙头" in row_df.columns else ""
        if stock_name == industry_leader_name:
            leader_remark = ""  # 自身不比较
        else:
            leader_growth_rate = row_df.get("行业龙头年增长率", [np.nan]).iloc[
                0] if "行业龙头年增长率" in row_df.columns else np.nan
            if not pd.isna(leader_growth_rate) and growth_rate > leader_growth_rate * 1.8:
                leader_remark = f"增速({growth_rate:.1%})远超龙头({leader_growth_rate:.1%})，需验证阿尔法真实性"
            else:
                leader_remark = ""

        # ---------- 10. 组装最终备注 ----------
        remark_parts = []
        if no_repo_remark:
            remark_parts.append(no_repo_remark)
        if ultra_growth_remark:
            remark_parts.append(ultra_growth_remark)
        if volatility_remark:
            remark_parts.append(volatility_remark)
        if leader_remark:
            remark_parts.append(leader_remark)
        if not remark_parts:
            remark_parts.append("适用PEG估值")
        final_remark = "；".join(remark_parts)

        # ---------- 11. 计算PE和股价 ----------
        PE_PEG80 = round(growth_rate * 80, 0)
        PE_PEG100 = round(growth_rate * 100, 0)
        PE_PEG120 = round(growth_rate * 120, 0)

        share_price_PEG80 = round(PE_PEG80 * next_year_EPS, 2)
        share_price_PEG100 = round(PE_PEG100 * next_year_EPS, 2)
        share_price_PEG120 = round(PE_PEG120 * next_year_EPS, 2)

        # 综合景气度（仅输出）
        industry_MoM_rate = row_df["当前季度同行业的同比增速"].iloc[0]
        integrated_bustling_rate = 0.7 * sequential_growth_contrast + 0.3 * industry_MoM_rate

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
        """辅助函数：返回全NaN的Series（用于PEG失效场景）"""
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


if __name__ == "__main__":
    INPUT_DIR = "E:\\BaiduSyncdisk\\IntegratedKM\\经济学\\股市投资建模"
    INPUT_FILE = "综合PE估值法估值.xlsx"
    INPUT_SHEET = "综合PE估值法估值"
    OUTPUT_DIR = "E:\\BaiduSyncdisk\\IntegratedKM\\经济学\\股市投资建模"
    OUTPUT_FILE = "综合PE估值法估值_结果.xlsx"
    OUTPUT_SHEET = INPUT_SHEET
    peg_model = peg_prediction_model()
    peg_model.main(INPUT_DIR, INPUT_FILE, INPUT_SHEET, OUTPUT_DIR, OUTPUT_FILE, OUTPUT_SHEET)
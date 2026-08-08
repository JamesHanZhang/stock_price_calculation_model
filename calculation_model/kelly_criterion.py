def calc_kelly_position(earning_rate: float, 
                        loss_rate: float, 
                        win_prob: float, 
                        kelly_fraction: float = 0.25) -> dict:
    """
    基于保守分数凯利公式计算当日建议仓位（满仓上限100%，不加杠杆）

    参数:
    -----
    earning_rate : float
        预计止盈收益率，如 20% 则输入 0.2
    loss_rate : float
        预计止损亏损率，如 10% 则输入 0.1
    win_prob : float
        赚钱的胜率，如 60% 则输入 0.6
    kelly_fraction : float, 默认=0.25
        分数凯利系数（保守程度）。0.25 表示 1/4 凯利，推荐新手；
        0.5 表示半凯利（激进）；1.0 表示全凯利（极危险）。

    返回:
    -----
    dict : 包含全凯利、分数凯利、最终执行仓位及风控提示
    """

    # ---------- 1. 严格入参校验 ----------
    if not (0 < earning_rate < 1 and 0 < loss_rate < 1):
        raise ValueError("止盈/亏损比例必须在 (0, 1) 之间，请勿输入百分比整数（如输入0.2而非20）")
    if not (0 < win_prob < 1):
        raise ValueError("胜率必须在 (0, 1) 之间")
    if not (0 < kelly_fraction <= 1.0):
        raise ValueError("分数系数必须在 (0, 1.0] 之间")

    # ---------- 2. 核心计算 ----------
    lose_prob = 1 - win_prob  # 赔率 q

    # 期望收益（单次下注的数学期望）
    expected_return = earning_rate * win_prob - loss_rate * lose_prob

    # 全凯利公式（无上限，允许杠杆）
    full_kelly = expected_return / (earning_rate * loss_rate)

    # 分数凯利（保守降仓）
    fractional_kelly = full_kelly * kelly_fraction

    # 最终执行仓位：硬性限定满仓 100%（即 1.0），并禁止负数（期望为负则归零）
    final_position = max(0.0, min(1.0, fractional_kelly))

    # ---------- 3. 决策逻辑与风控备注 ----------
    if expected_return <= 0:
        risk_note = "⚠️ 期望收益非正，数学模型拒绝开仓（建议空仓观望）"
    elif full_kelly > 1.0 and final_position == 1.0:
        risk_note = "✅ 保守公式已触发'满仓封顶'，当前为100%仓位，未加杠杆"
    elif final_position < 0.05:
        risk_note = "⚠️ 计算仓位极低（<5%），实际交易中建议放弃该机会"
    else:
        risk_note = "✅ 正常执行分数凯利仓位"

    # ---------- 4. 返回结构化结果 ----------
    return {
        "全凯利理论值 (允许杠杆)": round(full_kelly, 4),
        f"分数凯利 (系数={kelly_fraction})": round(fractional_kelly, 4),
        "最终执行仓位 (上限100%)": f"{round(final_position * 100, 2)}%",
        "对应资金倍数": f"{round(final_position, 4)} 倍 (1.0即满仓)",
        "风控建议": risk_note
    }


# ================= 使用示例（你的默认参数） =================
if __name__ == "__main__":
    # 样例输入：止盈20%，止损10%，胜率60%
    result = calc_kelly_position(
        earning_rate=0.0315, # 当日盈利的比例，按照赚钱的数学期望来算
        loss_rate=0.1, # 当日亏损的比例，按照亏损的数学期望来算
        win_prob=0.7, # 预计赚钱的胜率p
        kelly_fraction=0.25  # 保守1/4凯利（可手动改大，如改成0.5试试）
    )

    print("📊 凯利仓位计算结果（保守满仓版）：")
    for key, value in result.items():
        print(f"  {key}: {value}")

    # ---------- 额外测试：低胜率自动归零场景 ----------
    print("\n--- 边界测试（胜率仅30%，期望为负） ---")
    result_bad = calc_kelly_position(0.2, 0.1, 0.3)
    for key, value in result_bad.items():
        print(f"  {key}: {value}")
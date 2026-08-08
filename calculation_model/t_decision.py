# -*- coding: utf-8 -*-
"""
日内做T（正T vs 反T）期望 + 下行风险控制计算器
核心改进：
1. 引入「止盈比率（WIN_GAIN_RATIO）」—— 用收益换胜率
2. 引入「最大可容忍单情景亏损（MAX_ALLOWED_LOSS）」—— 硬性止损约束
3. 输出中包含「下行风险审计」，超标自动报警
4. 独立输出「正T日内最大亏损」与「反T日内最大亏损」
5. 【重要修正】正T和反T分别使用独立的失败惩罚系数，使最大亏损有实际区分度
"""

########### 公用参数（全局默认，通常不变）##########################
# ---------- 1. 振幅推导参数 ----------
AMPLITUDE_FACTOR = 1.5
BASE_AMPLITUDE = 0.01

# ---------- 2. 正T成功率（股市经验值） ----------
LONG_SR_UP = 0.85
LONG_SR_HIGH_END_HIGH = 0.70
LONG_SR_HIGH_END_LOW = 0.25
LONG_SR_LOW_V_UP = 0.80
LONG_SR_DOWN = 0.10

# ---------- 3. 反T成功率（股市经验值） ----------
SHORT_SR_UP = 0.15
SHORT_SR_HIGH_END_HIGH = 0.30
SHORT_SR_HIGH_END_LOW = 0.75
SHORT_SR_LOW_V_UP = 0.20
SHORT_SR_DOWN = 0.90

# ---------- 4. 失败惩罚系数（亏损幅度 = 振幅 × 惩罚） ----------
# 正T失败时亏损比例（通常正T在下跌市中亏损较大，故系数可设高一些）
LONG_FAILURE_PENALTY = 0.7
# 反T失败时亏损比例（反T在上涨市中亏损较大，但整体风险相对可控，系数可设低一些）
SHORT_FAILURE_PENALTY = 0.2   # 如果卖飞能立即在+1.6%内追回


def calc_t_with_risk_control(
    # ---------- 五类走势的概率（自动归一化） ----------
    p_up: float,
    p_open_high_end_high: float,
    p_open_high_end_low: float,
    p_open_low_v_up: float,
    p_down: float,

    # ---------- 五类走势的「持仓不动」盈亏比例 ----------
    hold_return_up: float,
    hold_return_high_end_high: float,
    hold_return_high_end_low: float,
    hold_return_low_v_up: float,
    hold_return_down: float,

    # ---------- 风险控制参数 ----------
    win_gain_ratio: float,          # 止盈比率（0~1）
    max_allowed_loss: float,        # 最大可容忍单情景亏损（负数）

    # ---------- 其他固定参数 ----------
    amplitude_factor: float,
    base_amplitude: float,
    long_sr_up: float,
    long_sr_high_end_high: float,
    long_sr_high_end_low: float,
    long_sr_low_v_up: float,
    long_sr_down: float,
    short_sr_up: float,
    short_sr_high_end_high: float,
    short_sr_high_end_low: float,
    short_sr_low_v_up: float,
    short_sr_down: float,
    long_failure_penalty: float,    # 正T失败惩罚系数
    short_failure_penalty: float,   # 反T失败惩罚系数

) -> dict:
    """
    返回：包含期望收益、下行风险审计、风控警告的完整结果
    """

    # ---------- 1. 概率归一化 ----------
    probs = [p_up, p_open_high_end_high, p_open_high_end_low, p_open_low_v_up, p_down]
    total = sum(probs)
    if abs(total - 1.0) > 0.001:
        probs = [p / total for p in probs]
    (p1, p2, p3, p4, p5) = probs

    # ---------- 2. 情景数据打包 ----------
    scenarios = [
        ("单边上涨", hold_return_up, long_sr_up, short_sr_up, p1),
        ("高开回落收涨", hold_return_high_end_high, long_sr_high_end_high, short_sr_high_end_high, p2),
        ("高开回落收跌", hold_return_high_end_low, long_sr_high_end_low, short_sr_high_end_low, p3),
        ("低开高走V型", hold_return_low_v_up, long_sr_low_v_up, short_sr_low_v_up, p4),
        ("单边下跌", hold_return_down, long_sr_down, short_sr_down, p5),
    ]

    # ---------- 3. 计算各情景收益（加入 win_gain_ratio） ----------
    long_exp_list = []
    short_exp_list = []
    details = []

    # 用于下行风险审计的列表
    long_worst_losses = []
    short_worst_losses = []

    for name, hold_ret, long_sr, short_sr, prob in scenarios:
        amplitude = abs(hold_ret) * amplitude_factor + base_amplitude

        # 成功盈利 = 振幅 × win_gain_ratio（只吃一部分）
        gain_take = amplitude * win_gain_ratio

        # 失败亏损分别使用各自的惩罚系数
        long_loss_take = amplitude * long_failure_penalty
        short_loss_take = amplitude * short_failure_penalty

        # 正T期望
        long_exp = long_sr * gain_take - (1 - long_sr) * long_loss_take
        # 反T期望
        short_exp = short_sr * gain_take - (1 - short_sr) * short_loss_take

        long_exp_list.append(long_exp)
        short_exp_list.append(short_exp)

        # 记录最坏情况亏损（即该情景下失败时的损失）
        long_worst = -long_loss_take if long_sr < 1 else 0
        short_worst = -short_loss_take if short_sr < 1 else 0
        long_worst_losses.append(long_worst)
        short_worst_losses.append(short_worst)

        details.append({
            "情景": name,
            "概率": prob,
            "持仓不动盈亏": hold_ret,
            "推导振幅": round(amplitude, 4),
            "正T成功率": long_sr,
            "正T期望": round(long_exp, 4),
            "正T最坏亏损": round(long_worst, 4),
            "反T成功率": short_sr,
            "反T期望": round(short_exp, 4),
            "反T最坏亏损": round(short_worst, 4),
        })

    # ---------- 4. 总体加权期望 ----------
    exp_long_total = sum(e * p for e, p in zip(long_exp_list, probs))
    exp_short_total = sum(e * p for e, p in zip(short_exp_list, probs))

    # ---------- 5. 下行风险审计 ----------
    long_worst_overall = min(long_worst_losses)
    short_worst_overall = min(short_worst_losses)

    long_risk_warning = long_worst_overall < max_allowed_loss
    short_risk_warning = short_worst_overall < max_allowed_loss

    # ---------- 6. 综合决策 ----------
    if long_risk_warning and short_risk_warning:
        best = "❌ 两者均存在超标风险，建议空仓观望"
        best_exp = 0
    elif long_risk_warning:
        best = "反T（先卖后买）【正T因风险超标被否决】"
        best_exp = exp_short_total
    elif short_risk_warning:
        best = "正T（先买后卖）【反T因风险超标被否决】"
        best_exp = exp_long_total
    else:
        if exp_long_total > exp_short_total:
            best = "正T（先买后卖）"
            best_exp = exp_long_total
        elif exp_short_total > exp_short_total:
            best = "反T（先卖后买）"
            best_exp = exp_short_total
        else:
            best = "两者无差异"
            best_exp = exp_long_total

    # ---------- 7. 纠错提示 ----------
    error_tips = []
    for d in details:
        name = d["情景"]
        le = d["正T期望"]
        se = d["反T期望"]
        lw = d["正T最坏亏损"]
        sw = d["反T最坏亏损"]

        if lw < max_allowed_loss:
            error_tips.append(f"🚨 【{name}】正T最坏亏损 {lw:.2%} 超过阈值 {max_allowed_loss:.2%}，该情景下正T风险不可接受！")
        if sw < max_allowed_loss:
            error_tips.append(f"🚨 【{name}】反T最坏亏损 {sw:.2%} 超过阈值 {max_allowed_loss:.2%}，该情景下反T风险不可接受！")

        if lw >= max_allowed_loss and sw >= max_allowed_loss:
            if le > se:
                better = "正T"
            elif se > le:
                better = "反T"
            else:
                better = "无差异"

            if best == "两者无差异" or better == "无差异":
                tip = f"【{name}】正T {le:.2%}，反T {se:.2%}。无显著优劣。"
            elif (best.startswith("正T") and better == "正T") or (best.startswith("反T") and better == "反T"):
                tip = f"✅ 【{name}】正T {le:.2%}，反T {se:.2%}。与最优方向一致。"
            else:
                diff = abs(se - le)
                if best.startswith("正T"):
                    tip = f"⚠️ 【{name}】若走出该情景，正T将跑输反T {diff:.2%}，建议纠错。"
                else:
                    tip = f"⚠️ 【{name}】若走出该情景，反T将跑输正T {diff:.2%}，建议纠错。"
            error_tips.append(tip)

    # ---------- 8. 返回结果 ----------
    return {
        "概率分布": {
            "单边上涨": f"{p1:.1%}",
            "高开回落收涨": f"{p2:.1%}",
            "高开回落收跌": f"{p3:.1%}",
            "低开高走V型": f"{p4:.1%}",
            "单边下跌": f"{p5:.1%}"
        },
        "止盈比率（收益换胜率）": f"{win_gain_ratio:.0%}",
        "最大可容忍单情景亏损": f"{max_allowed_loss:.2%}",
        "各情景明细": details,
        "总体期望": {
            "正T": f"{exp_long_total:.2%}",
            "反T": f"{exp_short_total:.2%}"
        },
        "正T日内最大亏损": f"{long_worst_overall:.2%}",
        "反T日内最大亏损": f"{short_worst_overall:.2%}",
        "下行风险审计": {
            "正T最坏情景亏损": f"{long_worst_overall:.2%}",
            "反T最坏情景亏损": f"{short_worst_overall:.2%}",
            "正T风险是否超标": "是" if long_risk_warning else "否",
            "反T风险是否超标": "是" if short_risk_warning else "否",
        },
        "最优方向": best,
        "期望差值": f"{abs(exp_long_total - exp_short_total):.2%}",
        "纠错提示": error_tips
    }


# ================= 独立的输出打印函数 =================
def print_results(result: dict) -> None:
    print("=" * 70)
    print("日内做T 期望 + 下行风险控制计算")
    print("=" * 70)

    print("\n📊 输入概率分布：")
    for k, v in result["概率分布"].items():
        print(f"  {k}: {v}")

    print(f"\n⚙️ 止盈比率（收益换胜率）：{result['止盈比率（收益换胜率）']}")
    print(f"⚙️ 最大可容忍单情景亏损：{result['最大可容忍单情景亏损']}")

    print("\n" + "-" * 70)
    print("📈 各情景明细（含最坏亏损审计）:")
    for d in result["各情景明细"]:
        print(f"  [{d['情景']}] 概率{d['概率']:.0%} | 振幅{d['推导振幅']:.1%} "
              f"| 正T: 成功率{d['正T成功率']:.0%} 期望{d['正T期望']:.2%} 最坏{d['正T最坏亏损']:.2%} "
              f"| 反T: 成功率{d['反T成功率']:.0%} 期望{d['反T期望']:.2%} 最坏{d['反T最坏亏损']:.2%}")

    print("\n" + "-" * 70)
    print("💰 总体加权期望收益：")
    for k, v in result["总体期望"].items():
        print(f"  {k}: {v}")

    # 高亮输出最大亏损（此时应已不同）
    print("\n" + "-" * 70)
    print("🔥 【日内最大潜在亏损（最坏情景压力测试）】")
    print(f"  正T（先买后卖）日内最大亏损：{result['正T日内最大亏损']}")
    print(f"  反T（先卖后买）日内最大亏损：{result['反T日内最大亏损']}")
    print(f"  注：正T和反T使用了不同的失败惩罚系数（分别为 {LONG_FAILURE_PENALTY:.1f} 和 {SHORT_FAILURE_PENALTY:.1f}），因此数值可能不同。")

    print("\n" + "-" * 70)
    print("🛡️ 下行风险审计（逐项检查）：")
    for k, v in result["下行风险审计"].items():
        print(f"  {k}: {v}")

    print("\n" + "-" * 70)
    print(f"🧭 最终决策（含风险约束）：{result['最优方向']}")
    if "期望差值" in result:
        print(f"   期望差值：{result['期望差值']}")

    print("\n" + "-" * 70)
    print("🆘 【纠错与风险预警】")
    for tip in result["纠错提示"]:
        print(f"  {tip}")

    print("\n" + "=" * 70)
    print("说明：")
    print("  1. 止盈比率（win_gain_ratio）越低，成功目标越容易达到，胜率越高，但每笔盈利减少。")
    print("  2. 「日内最大亏损」是判断策略生存能力的最核心指标，若超过账户承受极限，直接否决。")
    print("  3. 正T和反T的失败亏损系数独立设置，可分别调整以匹配实际交易中的风险特征。")
    print("  4. 决策顺序：先压测 → 再比期望 → 最后给方向。")
    print("=" * 70)


# ================= 所有参数在此集中配置 =================
if __name__ == "__main__":
    # ---------- 1. 五类走势的概率 ----------
    # 注：各项概率之和应约等于1，脚本会自动归一化处理。
    # P_UP：单边上涨概率（开盘即涨，全天无显著回调，收盘创日内新高或接近新高）
    P_UP = 0.6
    # P_OPEN_HIGH_END_HIGH：先涨后跌，尾盘收涨（高于开盘价）的概率
    # 即早盘冲高，盘中回落，但收盘价仍高于开盘价
    P_OPEN_HIGH_END_HIGH = 0.0
    # P_OPEN_HIGH_END_LOW：先涨后跌，尾盘收跌（低于开盘价）的概率
    # 即早盘冲高，盘中回落，收盘价低于开盘价（假突破）
    P_OPEN_HIGH_END_LOW = 0.25
    # P_OPEN_LOW_V_UP：先跌后涨（V型反转）的概率
    # 即早盘下挫，盘中V型拉起，收盘价高于开盘价或持平
    P_OPEN_LOW_V_UP = 0.00
    # P_DOWN：单边下跌概率（开盘即跌，全天无显著反弹，收盘创日内新低或接近新低）
    P_DOWN = 0.15

    # ---------- 2. 五类走势的「持仓不动」盈亏比例 ----------
    # 注：这里的盈亏比例是指「若该走势发生，仅持有底仓不做任何T操作，账户的当日盈亏比例」。
    # 正值表示盈利，负值表示亏损，输入小数（如0.10表示+10%，-0.08表示-8%）。
    # HOLD_RET_UP：单边上涨情景下的持仓盈亏比例
    HOLD_RET_UP = 0.10
    # HOLD_RET_HIGH_END_HIGH：先涨后跌、尾盘收涨情景下的持仓盈亏比例
    HOLD_RET_HIGH_END_HIGH = 0.06
    # HOLD_RET_HIGH_END_LOW：先涨后跌、尾盘收跌情景下的持仓盈亏比例（通常为负）
    HOLD_RET_HIGH_END_LOW = -0.08
    # HOLD_RET_LOW_V_UP：先跌后涨（V型反转）情景下的持仓盈亏比例（通常为正或微亏）
    HOLD_RET_LOW_V_UP = 0.00
    # HOLD_RET_DOWN：单边下跌情景下的持仓盈亏比例（通常为负）
    HOLD_RET_DOWN = -0.08

    # ---------- 3. 风险控制参数 ----------
    WIN_GAIN_RATIO = 1          # 止盈比率：成功时抓取振幅的比例（1表示全吃，0.5表示只吃一半）
    MAX_ALLOWED_LOSS = -0.1     # 最大可容忍单情景亏损（例如-0.1表示最多亏10%）

    # ========== 调用计算 ==========
    result = calc_t_with_risk_control(
        p_up=P_UP,
        p_open_high_end_high=P_OPEN_HIGH_END_HIGH,
        p_open_high_end_low=P_OPEN_HIGH_END_LOW,
        p_open_low_v_up=P_OPEN_LOW_V_UP,
        p_down=P_DOWN,

        hold_return_up=HOLD_RET_UP,
        hold_return_high_end_high=HOLD_RET_HIGH_END_HIGH,
        hold_return_high_end_low=HOLD_RET_HIGH_END_LOW,
        hold_return_low_v_up=HOLD_RET_LOW_V_UP,
        hold_return_down=HOLD_RET_DOWN,

        win_gain_ratio=WIN_GAIN_RATIO,
        max_allowed_loss=MAX_ALLOWED_LOSS,

        amplitude_factor=AMPLITUDE_FACTOR,
        base_amplitude=BASE_AMPLITUDE,

        long_sr_up=LONG_SR_UP,
        long_sr_high_end_high=LONG_SR_HIGH_END_HIGH,
        long_sr_high_end_low=LONG_SR_HIGH_END_LOW,
        long_sr_low_v_up=LONG_SR_LOW_V_UP,
        long_sr_down=LONG_SR_DOWN,

        short_sr_up=SHORT_SR_UP,
        short_sr_high_end_high=SHORT_SR_HIGH_END_HIGH,
        short_sr_high_end_low=SHORT_SR_HIGH_END_LOW,
        short_sr_low_v_up=SHORT_SR_LOW_V_UP,
        short_sr_down=SHORT_SR_DOWN,

        long_failure_penalty=LONG_FAILURE_PENALTY,
        short_failure_penalty=SHORT_FAILURE_PENALTY,
    )

    print_results(result)
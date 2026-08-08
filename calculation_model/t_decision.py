# -*- coding: utf-8 -*-
"""
日内做T（正T vs 反T）数学期望计算器
基于五类走势概率分布，量化评估最优T操作方向
"""


def calc_t_expectation(
        # 五类走势概率（输入默认值，和为1）
        p_up: float = 0.10,  # 1. 单边上涨概率 (e.g., 10%)
        p_open_high_end_high: float = 0.20,  # 2. 高开回落，收涨概率 (e.g., 20%)
        p_open_high_end_low: float = 0.30,  # 3. 高开回落，收跌概率 (e.g., 30%)
        p_open_low_v_up: float = 0.30,  # 4. 低开高走，V型反弹概率 (e.g., 30%)
        p_down: float = 0.10,  # 5. 单边下跌概率 (e.g., 10%)

        # 各情景下，正T与反T的收益率参数（可调整）
        # 情景1：单边上涨（正T赚，反T亏）
        profit_long_up: float = 0.05,
        profit_short_up: float = -0.05,

        # 情景2：高开回落，收涨（两者都能吃到波动利润）
        profit_long_high_end_high: float = 0.04,
        profit_short_high_end_high: float = 0.04,

        # 情景3：高开回落，收跌（两者都能吃到波动利润，幅度更大）
        profit_long_high_end_low: float = 0.06,
        profit_short_high_end_low: float = 0.06,

        # 情景4：低开高走V型（两者都能吃到波动利润）
        profit_long_low_v_up: float = 0.06,
        profit_short_low_v_up: float = 0.06,

        # 情景5：单边下跌（正T亏，反T赚）
        profit_long_down: float = -0.05,
        profit_short_down: float = 0.05,
) -> dict:
    """
    计算基于概率分布的做T期望收益
    """

    # ---------- 1. 概率校验与归一化 ----------
    prob_list = [p_up, p_open_high_end_high, p_open_high_end_low, p_open_low_v_up, p_down]
    total_prob = sum(prob_list)

    if abs(total_prob - 1.0) > 0.001:
        print(f"⚠️ 警告：输入概率之和为 {total_prob:.2%}，不等于 100%，脚本将自动归一化处理。")
        prob_list = [p / total_prob for p in prob_list]

    p_up, p_open_high_end_high, p_open_high_end_low, p_open_low_v_up, p_down = prob_list

    # ---------- 2. 核心期望计算 ----------
    # 正T（先买后卖）的期望收益
    E_long = (
            p_up * profit_long_up +
            p_open_high_end_high * profit_long_high_end_high +
            p_open_high_end_low * profit_long_high_end_low +
            p_open_low_v_up * profit_long_low_v_up +
            p_down * profit_long_down
    )

    # 反T（先卖后买）的期望收益
    E_short = (
            p_up * profit_short_up +
            p_open_high_end_high * profit_short_high_end_high +
            p_open_high_end_low * profit_short_high_end_low +
            p_open_low_v_up * profit_short_low_v_up +
            p_down * profit_short_down
    )

    # ---------- 3. 结果结构化 ----------
    results = {
        "概率分布": {
            "单边上涨": f"{p_up:.1%}",
            "高开回落，收涨": f"{p_open_high_end_high:.1%}",
            "高开回落，收跌": f"{p_open_high_end_low:.1%}",
            "低开高走V型": f"{p_open_low_v_up:.1%}",
            "单边下跌": f"{p_down:.1%}"
        },
        "期望收益": {
            "正T（先买后卖）": f"{E_long:.2%}",
            "反T（先卖后买）": f"{E_short:.2%}"
        },
        "最优方向": "反T（做空先卖）" if E_short > E_long else "正T（做多先买）" if E_long > E_short else "两者无差异",
        "优势幅度": f"{abs(E_short - E_long):.2%}"
    }

    return results

def print_result(result:dict):
    # 打印数值结果
    print("\n📊 【输入概率分布】")
    for k, v in result["概率分布"].items():
        print(f"  {k}: {v}")

    print("\n💰 【数学期望收益（基于盘中极限高低点）】")
    for k, v in result["期望收益"].items():
        print(f"  {k}: {v}")

    print("\n🧭 【决策建议】")
    print(f"  最优操作方向: {result['最优方向']}")
    print(f"  两者期望差值: {result['优势幅度']}")

    # ========= 补救措施提醒（核心风控） =========
    print("\n" + "=" * 60)
    print("🆘 【预测错误时的硬止损补救措施】")
    print("=" * 60)

    print("""
       1️⃣ 若你执行「反T（先卖）」，但实际走势是「单边上涨」：
          ✅ 补救规则：当股价盘中突破你卖出价位 +2% 且成交量放量（>5日均量），
             视为卖飞确认信号。必须无条件「纠错买回」，亏损控制在 -1% 以内。
             （操作：立即用市价买回同等数量，底仓不丢，只亏手续费和小幅踏空）

       2️⃣ 若你执行「正T（先买）」，但实际走势是「单边下跌」：
          ✅ 补救规则：当股价盘中跌破你买入价位 -1.5% 且持续放量下杀，
             视为买错确认信号。必须无条件「纠错止损」，亏损控制在 -1.5% 以内。
             （操作：立即卖出与买入数量相等的旧底仓，变相把新仓位砍掉，防止重仓被套）

       3️⃣ 终极保险（无论做正T还是反T）：
          ⏰ 尾盘 14:45 强制检查：若当日T操作未平仓（即买/卖的方向做反了），
             必须按市价反向回补，确保收盘时持股数量与开盘时完全一致。
             绝不留隔夜暴露头寸（除非你原本就计划加减仓）。
       """)

    print("\n" + "=" * 60)
    print("⚠️ 重要前提：以上期望值基于假设的波动幅度参数，")
    print("   请根据实际个股的历史日内振幅（ATR）调整上述 profit_* 数值。")
    print("=" * 60)

# ================= 运行示例（使用默认参数） =================
if __name__ == "__main__":

    print("=" * 60)
    print("日内做T（正T vs 反T）数学期望计算")
    print("=" * 60)

    # 调用默认参数（你也可以手动修改这里的数值）
    result = calc_t_expectation(
        p_up=0.30,  # 多少概率单边上涨
        p_open_high_end_high=0.30,  # 多少概率高开回落，收涨
        p_open_high_end_low=0.25,  # 多少概率高开回落，收跌
        p_open_low_v_up=0.15,  # 多少概率低开高走V型
        p_down=0.00  # 多少概率单边下跌（示例设定）
    )

    print_result(result)

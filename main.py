import pandas as pd

from pricing_model import PegPredictionModel

# 去耦合：关键列名集中定义，避免硬编码散落
STOCK_CODE_COLUMN = '股票代码'
STOCK_NAME_COLUMN = '股票名称'


def process_stocks(stock_data, ppm):
    """
    逐行处理股票数据（循环职责在main.py）
    输入: dict[股票代码 -> 行数据dict]
    输出: dict[股票代码 -> 输出dict]（仅含 ppm.new_column_lists 中的字段）
    注：本函数不引用任何具体列名，与Excel列名完全解耦
    """
    return {stock_code: ppm.process_row(row) for stock_code, row in stock_data.items()}


def main(input_dir, input_file, input_sheet, output_dir, output_file, output_sheet, output_summary_sheet):
    # 1. 读取Excel
    df = pd.read_excel(f"{input_dir}/{input_file}", sheet_name=input_sheet, header=0)

    # 2. DataFrame 转 dict（以股票代码为键，而非按records顺序）
    input_data = df.set_index(STOCK_CODE_COLUMN).to_dict('index')

    # 3. peg估值模型（逐行处理：输入单个dict，输出单个dict）
    ppm = PegPredictionModel()
    output_data = process_stocks(input_data, ppm)

    # 4. 合并输入与输出，构造完整结果DataFrame（恢复股票代码列+原始列顺序）
    merged_data = []
    for stock_code, row in input_data.items():
        merged = {STOCK_CODE_COLUMN: stock_code, **row, **output_data[stock_code]}
        merged_data.append(merged)
    df_full = pd.DataFrame(merged_data)
    # 恢复原始列顺序（输入列在前，输出列在后）
    df_full = df_full[df.columns.tolist() + ppm.new_column_lists]

    # 5. 构造仅含股票名称、股票代码及输出列的精简表
    summary_columns = [STOCK_NAME_COLUMN, STOCK_CODE_COLUMN] + ppm.new_column_lists
    df_summary = df_full[summary_columns]

    # 6. 写入Excel（完整数据sheet + 精简结果sheet）
    with pd.ExcelWriter(f"{output_dir}/{output_file}") as writer:
        df_full.to_excel(writer, sheet_name=output_sheet, index=False)
        df_summary.to_excel(writer, sheet_name=output_summary_sheet, index=False)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    INPUT_DIR = "/Users/jameszhang/DevProjects/data"
    INPUT_FILE = "综合PE估值法估值.xlsx"
    INPUT_SHEET = "综合PE估值法估值"
    OUTPUT_DIR = "/Users/jameszhang/DevProjects/data"
    OUTPUT_FILE = "综合PE估值法估值_结果.xlsx"
    OUTPUT_SHEET = INPUT_SHEET
    OUTPUT_SUMMARY_SHEET = "估值结果精简表"
    main(INPUT_DIR, INPUT_FILE, INPUT_SHEET, OUTPUT_DIR, OUTPUT_FILE, OUTPUT_SHEET, OUTPUT_SUMMARY_SHEET)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/

import pandas as pd

from pricing_model import PegPredictionModel

def main(input_dir, input_file, input_sheet, output_dir, output_file, output_sheet):
    df = pd.read_excel(f"{input_dir}\\{input_file}", sheet_name=input_sheet, header=0)
    # peg估值模型
    ppm = PegPredictionModel()
    df = ppm.main(df)
    df.to_excel(f"{output_dir}\\{output_file}", sheet_name=output_sheet, index=False)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    INPUT_DIR = "E:\\BaiduSyncdisk\\IntegratedKM\\经济学\\股市投资建模"
    INPUT_FILE = "综合PE估值法估值.xlsx"
    INPUT_SHEET = "综合PE估值法估值"
    OUTPUT_DIR = "E:\\BaiduSyncdisk\\IntegratedKM\\经济学\\股市投资建模"
    OUTPUT_FILE = "综合PE估值法估值_结果.xlsx"
    OUTPUT_SHEET = INPUT_SHEET
    main(INPUT_DIR, INPUT_FILE, INPUT_SHEET, OUTPUT_DIR, OUTPUT_FILE, OUTPUT_SHEET)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/

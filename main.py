import pandas as pd


def main(input_dir, input_file, input_sheet, output_dir, output_file, output_sheet):
    df = pd.read_excel(f"{input_dir}\\{input_file}", sheet_name=input_sheet, header=0)



# Press the green button in the gutter to run the script.
if __name__ == '__main__':


# See PyCharm help at https://www.jetbrains.com/help/pycharm/

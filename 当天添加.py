import os
import csv
import re
from datetime import datetime


def append_stock_data(source_csv_path, target_folder):
    """


    Args:
        source_csv_path: 包含所有股票代码和数据的源CSV文件路径
        target_folder: 存放各股票代码CSV文件的文件夹路径
    """
    # 获取当天日期，格式如 20260120（与目标文件中的日期格式一致）
    today_date = datetime.now().strftime("%Y%m%d")
    today_date =20260708
    if not os.path.exists(source_csv_path):
        print(f"错误：源文件 {source_csv_path} 不存在！")
        return

    # 检查目标文件夹是否存在
    if not os.path.exists(target_folder):
        print(f"错误：目标文件夹 {target_folder} 不存在！")
        return

    # 读取源CSV文件中的股票数据
    with open(source_csv_path, 'r', encoding='utf-8') as source_file:
        reader = csv.reader(source_file)
        next(reader)  # 跳过第一行

        # 遍历从第二行开始的每一行股票数据
        for row in reader:
            try:
                if len(row) < 3:
                    print(f"警告：当前行数据不完整（{row}），跳过...")
                    continue

                # ========== 核心修复：清理股票代码格式 ==========
                raw_code = row[0].strip()
                # 步骤1：用正则提取所有数字字符
                pure_digits = re.sub(r'\D', '', raw_code)  # 移除所有非数字字符（=、"、空格等）
                # 步骤2：补全为6位标准股票代码（不足6位前面补0，超过6位取后6位）
                stock_code = pure_digits.zfill(6)[-6:] if pure_digits else ""
                # =============================================

                # 跳过空代码行
                if not stock_code:
                    print(f"警告：原始代码 {raw_code} 提取不到有效数字，跳过...")
                    continue

                price = row[1].strip()
                volume = row[2].strip()

                # 构建正确的目标CSV文件路径（纯数字6位代码）
                target_csv_path = os.path.join(target_folder, f"{stock_code}.csv")

                # 检查目标文件是否存在
                if not os.path.exists(target_csv_path):
                    print(f"警告：未找到 {stock_code}.csv 文件（原始代码：{raw_code}），跳过...")
                    continue

                # 追加数据
                new_row = [today_date, price, volume]
                with open(target_csv_path, 'a', encoding='utf-8', newline='') as target_file:
                    writer = csv.writer(target_file)
                    writer.writerow(new_row)

                print(f"成功：{stock_code}.csv 已追加当天数据（原始代码：{raw_code}）")

            except IndexError as e:
                print(f"错误：当前行数据列数不足（{row}），{e}")
            except Exception as e:
                print(f"处理行 {row} 时出错：{str(e)}")




# -------------------------- 配置参数 --------------------------
# 替换为你的源CSV文件路径（包含所有股票代码和数据的文件）
# 替换为你的源CSV文件路径（包含所有股票代码和数据的文件）
SOURCE_CSV = "C:\\股票\\today data\\深证A股_处理后数据.csv"
# 替换为存放各股票代码CSV文件的文件夹路径
TARGET_FOLDER = "C:\\股票\\original data"
# -------------------------------------------------------------

# 执行主函数
if __name__ == "__main__":
    append_stock_data(SOURCE_CSV, TARGET_FOLDER)


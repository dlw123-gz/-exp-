
import pandas as pd
##记得修改日期
# 1. 文件路径（替换为你的本地文件路径）
file_path = r"C:\new_tdx\T0002\export\深证Ａ股20260708.xls" # 本地路径示例

# 2. 读取文件（完全适配该文件格式 + 限制仅读取前1490行）
# 关键新增参数：nrows=1490 限制读取行数
df = pd.read_csv(
    file_path,
    sep='\t',               # 核心：该文件是制表符分隔
    header=0,               # 跳过第1行标题，第2行是表头
    encoding='gbk',         # 适配中文编码，避免乱码
    usecols=[0, 3, 22, 23], # 提取目标列：第1列(0)、第4列(3)、第23列(22)、第24列(23)
    names=["代码", "名称", "内盘", "外盘"],  # 自定义列名，方便后续处理
    on_bad_lines='skip',    # 跳过解析错误的行（避免个别异常行中断）
    nrows=1490,             # 核心修改：仅读取前1490行数据（含表头行）
)

# 3. 数据清洗（确保内盘/外盘是数字，避免计算错误）
# 转换内盘/外盘为数字，无法转换的设为NaN
df["内盘"] = pd.to_numeric(df["内盘"], errors="coerce")
df["外盘"] = pd.to_numeric(df["外盘"], errors="coerce")
# 删除内盘/外盘为空的行（确保数据有效）
df = df.dropna(subset=["内盘", "外盘"])

# 4. 计算成交量（内盘 + 外盘）
df["成交量"] = df["内盘"] + df["外盘"]

# 5. 保留最终需要的列（代码、名称、成交量）
result_df = df[["代码", "名称", "成交量"]]

# 6. 保存结果到CSV（方便后续使用）
result_df.to_csv("C:\\股票\\today data\\深证A股_处理后数据.csv", index=False, encoding="utf-8-sig")

# 打印处理结果，确认正确性
print("✅ 数据处理完成！")
print(f"📊 读取的原始数据行数（限制1490行后）：{len(df)} 行")
print(f"📄 有效数据行数：{len(result_df)} 行")
print(f"💾 结果已保存到：C:\\Users\\dlw\Desktop\\today data\\深证A股_处理后数据2.csv")
print("\n🔍 前5行数据预览：")
print(result_df.head())
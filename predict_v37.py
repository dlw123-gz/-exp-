# -*- coding: utf-8 -*-
"""
V37 股票预测脚本
使用优化后的策略：prob>=0.80 & 连阳<3 & 昨日<7 & MA5<3
目标：预测明天可能涨停的股票
"""
import pandas as pd
import numpy as np
import os
import xgboost as xgb
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 配置
SOURCE_FOLDER = r"C:\股票\original data"
MODEL_PATH = r"C:\Users\dlw\Desktop\股票分析\涨停选股系统\models_final\model_v36_xgb.json"
OUTPUT_FOLDER = r"C:\Users\dlw\Desktop\股票分析\涨停选股系统\predictions"

# 最佳策略参数
PROB_THRESHOLD = 0.80
CONSEC_UP_MAX = 3
YESTERDAY_CHANGE_MAX = 7
MA5_POS_MAX = 3

# 特征列表
ALL_FEATURES = [
    '波动率_5d',
    '价格动量',
    '放量倍数_10d',
    '连阳天数',
    'RSI',
    'MACD',
    'MA5位置',
    '昨日涨幅',
    '前日涨幅',
]


def calculate_rsi(changes, period=14):
    """计算RSI"""
    if len(changes) < period:
        return 50.0
    gains = [c for c in changes[-period:] if c > 0]
    losses = [-c for c in changes[-period:] if c < 0]
    avg_gain = np.mean(gains) if gains else 0
    avg_loss = np.mean(losses) if losses else 0.001
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_macd(closes):
    """计算MACD"""
    if len(closes) < 26:
        return 0
    ema12 = pd.Series(closes).ewm(span=12, adjust=False).mean().iloc[-1]
    ema26 = pd.Series(closes).ewm(span=26, adjust=False).mean().iloc[-1]
    return (ema12 - ema26) / closes[-1] * 100 if closes[-1] > 0 else 0


def get_ma_position(close, ma5):
    """计算价格在MA5的位置"""
    return (close - ma5) / ma5 * 100 if ma5 > 0 else 0


def extract_features(df, idx):
    """提取特征"""
    if idx < 10 or idx >= len(df):
        return None

    row = df.iloc[idx]
    p1 = df.iloc[idx-1]
    p2 = df.iloc[idx-2]
    p3 = df.iloc[idx-3]
    p4 = df.iloc[idx-4]
    p5 = df.iloc[idx-5]

    # 计算10日均量
    vol_ma10 = df.iloc[max(0, idx-9):idx+1]['volume'].mean()

    # 计算波动率
    changes_5d = df.iloc[idx-4:idx+1]['涨幅'].tolist()
    vol_5d = np.std(changes_5d) if len(changes_5d) > 1 else 0

    # 价格动量
    price_momentum = (row['close'] - p5['close']) / p5['close'] if p5['close'] > 0 else 0

    # 连续上涨天数
    changes = [p5['涨幅'], p4['涨幅'], p3['涨幅'], p2['涨幅'], p1['涨幅']]
    consec_up = 0
    for c in reversed(changes):
        if c > 0.002:
            consec_up += 1
        else:
            break

    # RSI
    rsi = calculate_rsi(changes + [row['涨幅']])

    # MACD
    closes = df.iloc[max(0, idx-25):idx+1]['close'].tolist()
    macd = calculate_macd(closes)

    # MA5位置
    ma5 = df.iloc[max(0, idx-4):idx+1]['close'].mean()
    ma_pos = get_ma_position(row['close'], ma5)

    features = {
        '波动率_5d': vol_5d,
        '价格动量': price_momentum,
        '放量倍数_10d': row['volume'] / vol_ma10 if vol_ma10 > 0 else 1,
        '连阳天数': consec_up,
        'RSI': rsi,
        'MACD': macd,
        'MA5位置': ma_pos,
        '昨日涨幅': p1['涨幅'] * 100,
        '前日涨幅': p2['涨幅'] * 100,
    }

    return features


def load_stocks():
    """加载所有股票数据"""
    print("Loading stocks...")
    stocks = {}
    for i, filename in enumerate(os.listdir(SOURCE_FOLDER)):
        if i % 300 == 0:
            print(f"  {i}")
        if filename.endswith('.csv'):
            code = os.path.splitext(filename)[0]
            try:
                df = pd.read_csv(os.path.join(SOURCE_FOLDER, filename), header=None, skiprows=1)
                df.rename(columns={0: 'date', 1: 'close', 2: 'volume'}, inplace=True)
                df['volume'] = df['volume'].astype(int) // 100
                df['涨幅'] = df['close'].pct_change().fillna(0.0)
                stocks[code] = df
            except:
                continue
    print(f"Loaded {len(stocks)} stocks")
    return stocks


def predict_tomorrow(stocks, model):
    """预测明天可能涨停的股票"""
    print("\n" + "="*60)
    print("Predicting Tomorrow's Stocks")
    print("="*60)
    print(f"\n策略条件:")
    print(f"  预测概率 >= {PROB_THRESHOLD}")
    print(f"  连阳天数 < {CONSEC_UP_MAX}")
    print(f"  昨日涨幅 < {YESTERDAY_CHANGE_MAX}%")
    print(f"  MA5位置 < {MA5_POS_MAX}%")
    print()

    predictions = []

    for code, df in stocks.items():
        if len(df) < 11:
            continue

        # 获取最新一天的数据
        latest_idx = len(df) - 1
        row = df.iloc[latest_idx]

        # 跳过今天已经大涨的股票（避免追高）
        today_change = row['涨幅'] * 100
        if today_change > 6:  # 今日涨幅超过6%不推荐
            continue

        features = extract_features(df, latest_idx)
        if features is None:
            continue

        # 提取特征进行预测
        X = np.array([[features[f] for f in ALL_FEATURES]])
        dtest = xgb.DMatrix(X, feature_names=ALL_FEATURES)
        prob = model.predict(dtest)[0]

        # 获取昨天的日期作为参考
        yesterday_change = features['昨日涨幅']
        consec_up = features['连阳天数']
        ma_pos = features['MA5位置']

        # 应用筛选条件
        if (prob >= PROB_THRESHOLD and
            consec_up < CONSEC_UP_MAX and
            yesterday_change < YESTERDAY_CHANGE_MAX and
            ma_pos < MA5_POS_MAX):

            # 获取今日收盘价和成交量
            today_close = row['close']
            today_volume = row['volume']
            yesterday_close = df.iloc[latest_idx-1]['close']

            predictions.append({
                '股票代码': code,
                '股票名称': get_stock_name(code),
                '预测概率': prob,
                '今日收盘价': today_close,
                '今日涨幅': today_change,
                '今日成交量(手)': today_volume,
                '昨日涨幅': yesterday_change,
                '前日涨幅': features['前日涨幅'],
                '连阳天数': consec_up,
                'MA5位置': ma_pos,
                '放量倍数': features['放量倍数_10d'],
                'RSI': features['RSI'],
                'MACD': features['MACD'],
                '价格动量': features['价格动量'] * 100,
            })

    # 按预测概率排序
    predictions.sort(key=lambda x: x['预测概率'], reverse=True)

    return predictions


def get_stock_name(code):
    """获取股票名称（如果有的话）"""
    # 这里可以根据实际情况从股票列表中获取名称
    # 目前简单返回代码
    return code


def save_predictions(predictions, prefix="tomorrow"):
    """保存预测结果"""
    if not predictions:
        print("没有符合条件的股票")
        return

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    # 生成文件名
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    filename = f"{OUTPUT_FOLDER}/predictions_{prefix}_{date_str}.csv"

    # 保存为CSV
    df = pd.DataFrame(predictions)
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    print(f"\n预测结果已保存到: {filename}")
    return filename


def print_predictions(predictions, top_n=10):
    """打印预测结果"""
    if not predictions:
        print("没有符合条件的股票！")
        return

    print(f"\n{'='*80}")
    print(f"明天重点关注股票 (共 {len(predictions)} 只)")
    print(f"{'='*80}")
    print()

    # 打印表头
    print(f"{'代码':<10} {'名称':<8} {'概率':>6} {'今日涨':>6} {'昨日涨':>6} {'连阳':>4} {'MA5':>5} {'放量':>5}")
    print("-" * 80)

    # 打印前N个
    for i, p in enumerate(predictions[:top_n]):
        print(f"{p['股票代码']:<10} {p['股票名称']:<8} {p['预测概率']*100:>5.1f}% "
              f"{p['今日涨幅']:>6.2f}% {p['昨日涨幅']:>6.2f}% {p['连阳天数']:>4} "
              f"{p['MA5位置']:>5.2f}% {p['放量倍数']:>5.2f}x")

    if len(predictions) > top_n:
        print(f"\n... 还有 {len(predictions) - top_n} 只股票")
        print()

    # 打印详细统计
    print(f"\n{'='*80}")
    print("统计信息:")
    print(f"{'='*80}")
    print(f"  符合条件的股票总数: {len(predictions)}")
    print(f"  平均预测概率: {np.mean([p['预测概率'] for p in predictions])*100:.2f}%")
    print(f"  最高预测概率: {max([p['预测概率'] for p in predictions])*100:.2f}%")
    print(f"  平均今日涨幅: {np.mean([p['今日涨幅'] for p in predictions]):.2f}%")
    print(f"  平均连阳天数: {np.mean([p['连阳天数'] for p in predictions]):.2f}")

    # 按概率区间分组
    high_prob = [p for p in predictions if p['预测概率'] >= 0.85]
    medium_prob = [p for p in predictions if 0.80 <= p['预测概率'] < 0.85]

    print(f"\n  高概率股票 (>=85%): {len(high_prob)} 只")
    print(f"  中概率股票 (80-85%): {len(medium_prob)} 只")

    return predictions


def main():
    """主函数"""
    print("="*60)
    print("V37 股票预测系统")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # 加载模型
    print("\nLoading model...")
    model = xgb.Booster()
    model.load_model(MODEL_PATH)
    print(f"Model loaded from: {MODEL_PATH}")

    # 加载股票数据
    stocks = load_stocks()

    # 预测
    predictions = predict_tomorrow(stocks, model)

    # 打印结果
    print_predictions(predictions, top_n=15)

    # 保存结果
    save_predictions(predictions, prefix="v37")

    print("\n" + "="*60)
    print("预测完成!")
    print("="*60)


if __name__ == "__main__":
    main()

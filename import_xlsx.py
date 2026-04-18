"""
数据导入脚本

将 Excel 数据导入 MySQL 数据库

使用说明：
1. 准备数据文件（参考 data/README.md 的格式要求）
2. 修改本文件中的 XLSX_PATH 为你的数据文件路径
3. 确保 backend/config_local.py 中的数据库配置正确
4. 运行: python import_xlsx.py
"""

import pandas as pd
import pymysql
import warnings
import os
import sys

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from config import DB_CONFIG

# 配置：修改为你的数据文件路径
XLSX_PATH = os.path.join(os.path.dirname(__file__), 'data', 'your_data.xlsx')
SHEET_NAME = 'Sheet1'  # 修改为你的工作表名称

TABLE_NAME = "data_380"

# 字段映射（根据你的实际数据调整）
COLUMN_MAP = {
    # 示例映射，请根据实际列名修改
    '结算编码': 'settle_code',
    '结算客户': 'settle_name',
    '省区平台': 'province',
    '城市': 'city',
    '行业': 'industry',
    '项目简称': 'project_name',
    '日期': 'report_date',
    '业绩量': 'performance',
    '销售收入': 'sales_revenue',
    '经营利润': 'operating_profit',
    # 添加更多字段...
}

# MySQL 建表语句（根据实际字段调整）
CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id INT AUTO_INCREMENT PRIMARY KEY,
    settle_code VARCHAR(50),
    settle_name VARCHAR(255),
    province VARCHAR(100),
    city VARCHAR(100),
    industry VARCHAR(50),
    project_name VARCHAR(100),
    report_date DATE,
    performance DECIMAL(20,2) DEFAULT 0,
    sales_revenue DECIMAL(20,2) DEFAULT 0,
    operating_profit DECIMAL(20,2) DEFAULT 0,
    INDEX idx_province (province),
    INDEX idx_industry (industry),
    INDEX idx_report_date (report_date),
    INDEX idx_settle_code (settle_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

BATCH_SIZE = 2000


def main():
    print("=" * 50)
    print("380平台数据导入工具")
    print("=" * 50)

    # 检查文件
    if not os.path.exists(XLSX_PATH):
        print(f"\n[错误] 找不到数据文件: {XLSX_PATH}")
        print("请修改 XLSX_PATH 指向你的数据文件")
        return

    # 1. 读取 Excel
    print(f"\n[1/4] 读取 Excel 文件...")
    try:
        df = pd.read_excel(XLSX_PATH, sheet_name=SHEET_NAME)
        print(f"    总行数: {len(df)}, 总列数: {len(df.columns)}")
        print(f"    列名: {list(df.columns)}")
    except Exception as e:
        print(f"[错误] 读取 Excel 失败: {e}")
        return

    # 2. 重命名列
    print("\n[2/4] 处理数据...")
    # 只保留存在的列
    valid_map = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=valid_map)
    
    # 日期处理
    if 'report_date' in df.columns:
        df['report_date'] = pd.to_datetime(df['report_date'], errors='coerce').dt.date
    
    # 数值列处理
    numeric_cols = ['performance', 'sales_revenue', 'operating_profit']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 3. 连接数据库
    print("\n[3/4] 连接 MySQL，创建表...")
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        cur.execute(CREATE_TABLE_SQL)
        conn.commit()
        print(f"    表 {TABLE_NAME} 已创建")
    except Exception as e:
        print(f"[错误] 数据库连接失败: {e}")
        return

    # 4. 批量插入
    print(f"\n[4/4] 批量导入数据...")
    cols = [c for c in df.columns if c in valid_map.values() or c in ['settle_code', 'settle_name', 'province', 'city', 'industry', 'project_name', 'report_date', 'performance', 'sales_revenue', 'operating_profit']]
    df = df[[c for c in cols if c in df.columns]]
    
    placeholders = ','.join(['%s'] * len(df.columns))
    insert_sql = f"INSERT INTO {TABLE_NAME} ({','.join(df.columns)}) VALUES ({placeholders})"

    total = len(df)
    for i in range(0, total, BATCH_SIZE):
        batch = df.iloc[i:i+BATCH_SIZE]
        values = [tuple(row) for row in batch.values]
        cur.executemany(insert_sql, values)
        conn.commit()
        done = min(i + BATCH_SIZE, total)
        print(f"    进度: {done}/{total} ({done*100//total}%)")

    # 验证
    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
    count = cur.fetchone()[0]
    print(f"\n导入完成！总记录数: {count}")
    conn.close()


if __name__ == "__main__":
    main()

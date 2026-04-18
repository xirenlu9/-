"""
FastAPI 后端 - 380平台数据可视化 + 异常告警系统
内部账号系统 + 告警历史记录
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from decimal import Decimal
import pymysql
import json
import os
import hashlib
import secrets
import hashlib as _hl  # alias to avoid shadowing
from datetime import datetime, timedelta
from typing import List, Optional

# ────────── 数据库配置 ──────────
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "stock_db",
    "charset": "utf8mb4",
}

def get_conn():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

def decimal_to_float(v):
    if isinstance(v, Decimal):
        return float(v)
    return v

def row_to_float(row: dict) -> dict:
    result = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            result[k] = float(v)
        elif hasattr(v, 'strftime'):
            result[k] = str(v)
        else:
            result[k] = v
    return result

# ────────── FastAPI 初始化 ──────────
app = FastAPI(title="380平台数据可视化 API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ══════════════════════════════════════════════════════
# 启动时建表
# ══════════════════════════════════════════════════════
@app.on_event("startup")
def on_startup():
    conn = get_conn()
    cur = conn.cursor()
    # 用户表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alert_users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(128) NOT NULL,
            display_name VARCHAR(100),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    # 告警历史表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alert_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            severity VARCHAR(10),
            province VARCHAR(100),
            settle_name VARCHAR(200),
            industry VARCHAR(50),
            project_name VARCHAR(200),
            report_date DATE,
            metric VARCHAR(30),
            metric_name VARCHAR(30),
            cur_value DECIMAL(20,2),
            prev_value DECIMAL(20,2),
            change_rate DECIMAL(10,2),
            reason TEXT,
            INDEX idx_user_detected (user_id, detected_at),
            INDEX idx_severity (severity)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    conn.close()
    print("[OK] Tables initialized")

# ══════════════════════════════════════════════════════
# 认证工具
# ══════════════════════════════════════════════════════
def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    return secrets.token_hex(24)

def get_current_user(x_token: Optional[str] = Header(None)) -> dict:
    if not x_token:
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, display_name, last_login FROM alert_users WHERE 1=1")  # dummy
    # 用 SQL 直接验证 token
    cur.execute("""
        SELECT id, username, display_name, last_login FROM alert_users
        WHERE MD5(CONCAT(id, username)) = %s
    """, (x_token[:32] if len(x_token) >= 32 else x_token,))
    user = cur.fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return user

# ══════════════════════════════════════════════════════
# 认证 API
# ══════════════════════════════════════════════════════
class RegisterReq(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = ""

class LoginReq(BaseModel):
    username: str
    password: str

@app.post("/api/auth/register")
def register(body: RegisterReq):
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM alert_users WHERE username = %s", (body.username,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="用户名已存在")
    pw_hash = hash_pw(body.password)
    cur.execute("""
        INSERT INTO alert_users (username, password_hash, display_name)
        VALUES (%s, %s, %s)
    """, (body.username, pw_hash, body.display_name or body.username))
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return {"success": True, "message": "注册成功，请登录", "user_id": user_id}

@app.post("/api/auth/login")
def login(body: LoginReq):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash, display_name FROM alert_users WHERE username = %s", (body.username,))
    user = cur.fetchone()
    if not user or hash_pw(body.password) != user['password_hash']:
        conn.close()
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    # 更新最后登录时间
    cur.execute("UPDATE alert_users SET last_login = NOW() WHERE id = %s", (user['id'],))
    conn.commit()
    # 生成简单 token（用 username+id 的 md5）
    token = _hl.md5(f"{user['id']}{user['username']}".encode()).hexdigest()
    conn.close()
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "display_name": user['display_name'] or user['username'],
        }
    }

@app.get("/api/auth/me")
def get_me(x_token: Optional[str] = Header(None)):
    if not x_token:
        return {"logged_in": False}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, username, display_name, last_login, created_at FROM alert_users
        WHERE MD5(CONCAT(id, username)) = %s
    """, (x_token[:32] if len(x_token) >= 32 else x_token,))
    user = cur.fetchone()
    conn.close()
    if not user:
        return {"logged_in": False}
    return {
        "logged_in": True,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "display_name": user['display_name'] or user['username'],
            "last_login": str(user['last_login']) if user['last_login'] else None,
        }
    }

# ══════════════════════════════════════════════════════
# 异常检测引擎
# ══════════════════════════════════════════════════════
def detect_380_anomalies(industry_filter: str = "") -> list:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT report_date FROM data_380
        GROUP BY report_date ORDER BY report_date DESC LIMIT 2
    """)
    recent_months = [str(r['report_date']) for r in cur.fetchall()]
    if len(recent_months) < 2:
        conn.close()
        return []
    cur_month_str, prev_month_str = recent_months[0], recent_months[1]

    query = f"""
        SELECT province, settle_name, industry, project_name,
               report_date, performance, sales_revenue, operating_profit
        FROM data_380
        WHERE report_date IN ('{cur_month_str}', '{prev_month_str}')
    """
    if industry_filter:
        query += f" AND industry = '{industry_filter}'"
    cur.execute(query)
    raw = cur.fetchall()

    by_proj = {}
    for r in raw:
        key = (str(r['province']), str(r['settle_name']), str(r['industry']), str(r['project_name']))
        if key not in by_proj:
            by_proj[key] = {}
        by_proj[key][str(r['report_date'])] = row_to_float(r)

    metrics = ["performance", "sales_revenue", "operating_profit"]
    metric_names = {"performance": "业绩", "sales_revenue": "收入", "operating_profit": "利润"}
    ind_stats = {}

    cur.execute(f"""
        SELECT industry, {', '.join([
            f"AVG({m}) as mean_{m}, STDDEV({m}) as std_{m}"
            for m in metrics
        ])}
        FROM data_380
        WHERE performance > 0
        GROUP BY industry
    """)
    for r in cur.fetchall():
        ind_stats[r['industry']] = {
            m: {
                'mean': decimal_to_float(r.get(f'mean_{m}')) or 0,
                'std': decimal_to_float(r.get(f'std_{m}')) or 0,
            }
            for m in metrics
        }

    anomalies = []
    for (province, settle, industry, proj), months_data in by_proj.items():
        if len(months_data) < 2:
            continue
        sorted_months = sorted(months_data.keys())
        cur_month = months_data[sorted_months[-1]]
        prev_month = months_data[sorted_months[-2]]
        stats = ind_stats.get(industry, {})

        for m in metrics:
            cur_val = cur_month.get(m) or 0
            prev_val = prev_month.get(m) or 0
            if prev_val == 0:
                continue

            change_rate = (cur_val - prev_val) / abs(prev_val)
            reasons, severity = [], "low"
            st = stats.get(m, {})
            mean, std = st.get('mean', 0), st.get('std', 0)

            if std > 0 and abs(cur_val - mean) > 3 * std:
                reasons.append(f"绝对值异常（当前={cur_val:.0f}，行业均值={mean:.0f}）")
                severity = "high"

            if abs(change_rate) > 0.5:
                reasons.append(f"环比{change_rate*100:+,.1f}%（{prev_val:.0f}→{cur_val:.0f}）")
                if severity == "low":
                    severity = "medium"

            if abs(cur_val) < 100 and prev_val > 1000:
                reasons.append("业绩骤降")
                severity = "high"

            if reasons:
                anomalies.append({
                    "province": province,
                    "settle_name": settle,
                    "industry": industry,
                    "project_name": proj,
                    "report_date": cur_month.get('report_date', sorted_months[-1]),
                    "metric": m,
                    "metric_name": metric_names.get(m, m),
                    "cur_value": round(cur_val, 2),
                    "prev_value": round(prev_val, 2),
                    "change_rate": round(change_rate * 100, 2),
                    "reason": "；".join(reasons),
                    "severity": severity,
                })

    conn.close()
    order = {"high": 0, "medium": 1, "low": 2}
    anomalies.sort(key=lambda x: order.get(x["severity"], 3))
    return anomalies[:200]

# ══════════════════════════════════════════════════════
# 异常告警 API（需登录）
# ══════════════════════════════════════════════════════
@app.get("/api/alert/detect")
def api_alert_detect(
    industry: str = "",
    x_token: Optional[str] = Header(None),
):
    """触发异常检测，结果保存到当前用户的历史记录"""
    get_current_user(x_token)  # 验证登录
    anomalies = detect_380_anomalies(industry_filter=industry if industry != "全部" else "")

    # 取出用户ID
    token = x_token[:32] if x_token and len(x_token) >= 32 else (x_token or "")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM alert_users WHERE MD5(CONCAT(id, username)) = %s
    """, (token,))
    user_row = cur.fetchone()
    user_id = user_row['id'] if user_row else 0

    if user_id and anomalies:
        # 批量写入历史记录
        vals = [
            (user_id, a['severity'], a['province'], a['settle_name'], a['industry'],
             a['project_name'], a['report_date'], a['metric'], a['metric_name'],
             a['cur_value'], a['prev_value'], a['change_rate'], a['reason'])
            for a in anomalies
        ]
        cur.executemany("""
            INSERT INTO alert_history
            (user_id, severity, province, settle_name, industry, project_name,
             report_date, metric, metric_name, cur_value, prev_value, change_rate, reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, vals)
        conn.commit()
    conn.close()

    return {
        "total": len(anomalies),
        "high": len([a for a in anomalies if a["severity"] == "high"]),
        "medium": len([a for a in anomalies if a["severity"] == "medium"]),
        "low": len([a for a in anomalies if a["severity"] == "low"]),
        "saved": len(anomalies),
        "data": anomalies[:100],
    }

@app.get("/api/alert/history")
def api_alert_history(
    page: int = 1,
    limit: int = 30,
    severity: str = "",
    industry: str = "",
    keyword: str = "",
    x_token: Optional[str] = Header(None),
):
    """获取当前用户的告警历史记录，支持关键词搜索"""
    user = get_current_user(x_token)
    conn = get_conn()
    cur = conn.cursor()

    where = ["user_id = %s"]
    params = [user['id']]
    if severity:
        where.append("severity = %s")
        params.append(severity)
    if industry:
        where.append("industry = %s")
        params.append(industry)
    if keyword:
        where.append("(project_name LIKE %s OR province LIKE %s OR settle_name LIKE %s OR reason LIKE %s)")
        pat = f"%{keyword}%"
        params.extend([pat, pat, pat, pat])

    # 总数
    cur.execute(f"SELECT COUNT(*) as cnt FROM alert_history WHERE {' AND '.join(where)}", params)
    total = cur.fetchone()['cnt']

    # 分页数据
    offset = (page - 1) * limit
    cur.execute(f"""
        SELECT id, detected_at, severity, province, settle_name, industry,
               project_name, report_date, metric, metric_name,
               cur_value, prev_value, change_rate, reason
        FROM alert_history
        WHERE {' AND '.join(where)}
        ORDER BY detected_at DESC,
        CASE severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END
        LIMIT %s OFFSET %s
    """, params + [limit, offset])
    rows = cur.fetchall()
    conn.close()

    return {
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "data": [row_to_float(r) for r in rows],
    }

@app.delete("/api/alert/history/{alert_id}")
def api_delete_alert(alert_id: int, x_token: Optional[str] = Header(None)):
    """删除单条告警记录"""
    user = get_current_user(x_token)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM alert_history WHERE id = %s AND user_id = %s", (alert_id, user['id']))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        raise HTTPException(status_code=404, detail="记录不存在或无权删除")
    return {"success": True, "message": "已删除"}

@app.delete("/api/alert/history")
def api_clear_history(x_token: Optional[str] = Header(None)):
    """清空当前用户所有历史记录"""
    user = get_current_user(x_token)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM alert_history WHERE user_id = %s", (user['id'],))
    conn.commit()
    count = cur.rowcount
    conn.close()
    return {"success": True, "cleared": count}

@app.get("/api/alert/stats")
def api_alert_stats(x_token: Optional[str] = Header(None)):
    """获取当前用户的告警统计"""
    user = get_current_user(x_token)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT severity, COUNT(*) as cnt
        FROM alert_history WHERE user_id = %s
        GROUP BY severity
    """, (user['id'],))
    rows = cur.fetchall()
    cur.execute("""
        SELECT DATE_FORMAT(detected_at, '%Y-%m-%d') as day, COUNT(*) as cnt
        FROM alert_history WHERE user_id = %s
        GROUP BY DATE_FORMAT(detected_at, '%Y-%m-%d')
        ORDER BY day DESC LIMIT 30
    """, (user['id'],))
    trend = cur.fetchall()
    conn.close()
    stats = {r['severity']: r['cnt'] for r in rows}
    return {
        "total": sum(stats.values()),
        "high": stats.get('high', 0),
        "medium": stats.get('medium', 0),
        "low": stats.get('low', 0),
        "trend": [row_to_float(r) for r in trend],
    }

# ══════════════════════════════════════════════════════
# 380 平台数据接口
# ══════════════════════════════════════════════════════

@app.get("/api/380/overview")
def api_380_overview():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as total_records, COUNT(DISTINCT settle_code) as project_count,
               COUNT(DISTINCT province) as province_count, COUNT(DISTINCT industry) as industry_count,
               MIN(report_date) as min_date, MAX(report_date) as max_date
        FROM data_380
    """)
    base = row_to_float(cur.fetchone())
    for alias, sql in [
        ("total_performance", "SELECT SUM(performance) FROM data_380 WHERE performance>0"),
        ("total_revenue", "SELECT SUM(sales_revenue) FROM data_380 WHERE sales_revenue>0"),
        ("total_operating_profit", "SELECT SUM(operating_profit) FROM data_380"),
        ("total_payment", "SELECT SUM(payment_amount) FROM data_380 WHERE payment_amount>0"),
    ]:
        cur.execute(sql)
        row = cur.fetchone()
        # 列名可能是 SUM(xxx) 或类似聚合名
        val = next((v for v in row.values() if v is not None), 0)
        base[alias] = decimal_to_float(val)
    conn.close()
    return base

@app.get("/api/380/byIndustry")
def api_380_by_industry():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT industry, COUNT(*) as record_count, SUM(performance) as total_perf,
               SUM(sales_revenue) as total_rev, SUM(operating_profit) as total_op,
               SUM(payment_amount) as total_pay,
               AVG(operating_profit/NULLIF(performance,0)*100) as profit_rate
        FROM data_380 WHERE performance > 0 GROUP BY industry ORDER BY total_perf DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return {"data": [row_to_float(r) for r in rows]}

@app.get("/api/380/byProvince")
def api_380_by_province(industry: str = ""):
    conn = get_conn()
    cur = conn.cursor()
    if industry:
        cur.execute("""
            SELECT province, industry, COUNT(*) as record_count,
                   SUM(performance) as total_perf, SUM(sales_revenue) as total_rev,
                   SUM(operating_profit) as total_op
            FROM data_380 WHERE industry=%s AND performance>0
            GROUP BY province, industry ORDER BY total_perf DESC LIMIT 36
        """, (industry,))
    else:
        cur.execute("""
            SELECT province, industry, COUNT(*) as record_count,
                   SUM(performance) as total_perf, SUM(sales_revenue) as total_rev,
                   SUM(operating_profit) as total_op
            FROM data_380 WHERE performance>0
            GROUP BY province, industry ORDER BY total_perf DESC LIMIT 100
        """)
    rows = cur.fetchall()
    conn.close()
    return {"data": [row_to_float(r) for r in rows]}

@app.get("/api/380/trend")
def api_380_trend(industry: str = ""):
    conn = get_conn()
    cur = conn.cursor()
    if industry:
        cur.execute(f"""
            SELECT DATE_FORMAT(report_date,'%Y-%m') as month,
                   SUM(performance) as perf, SUM(sales_revenue) as rev,
                   SUM(operating_profit) as op_profit
            FROM data_380 WHERE industry='{industry}'
            GROUP BY DATE_FORMAT(report_date,'%Y-%m') ORDER BY month ASC
        """)
    else:
        cur.execute("""
            SELECT DATE_FORMAT(report_date,'%Y-%m') as month,
                   SUM(performance) as perf, SUM(sales_revenue) as rev,
                   SUM(operating_profit) as op_profit
            FROM data_380 GROUP BY DATE_FORMAT(report_date,'%Y-%m') ORDER BY month ASC
        """)
    rows = cur.fetchall()
    conn.close()
    return {"data": [row_to_float(r) for r in rows]}

@app.get("/api/380/search")
def api_380_search(q: str = "", limit: int = 20, industry: str = ""):
    """全局搜索：按项目名/省份/结算主体关键词搜索 380 数据"""
    if not q or len(q) < 1:
        return {"projects": [], "provinces": [], "industries": []}
    pat = f"%{q}%"
    conn = get_conn()
    cur = conn.cursor()

    # 项目搜索
    if industry:
        cur.execute("""
            SELECT DISTINCT settle_name, province, industry, project_name,
                   SUM(performance) as total_perf
            FROM data_380
            WHERE industry=%s AND (project_name LIKE %s OR settle_name LIKE %s OR province LIKE %s)
            GROUP BY settle_name, province, industry, project_name
            ORDER BY total_perf DESC LIMIT %s
        """, (industry, pat, pat, pat, limit))
    else:
        cur.execute("""
            SELECT DISTINCT settle_name, province, industry, project_name,
                   SUM(performance) as total_perf
            FROM data_380
            WHERE project_name LIKE %s OR settle_name LIKE %s OR province LIKE %s
            GROUP BY settle_name, province, industry, project_name
            ORDER BY total_perf DESC LIMIT %s
        """, (pat, pat, pat, limit))
    projects = [row_to_float(r) for r in cur.fetchall()]

    # 省份匹配
    cur.execute("""
        SELECT DISTINCT province, SUM(performance) as total_perf
        FROM data_380 WHERE province LIKE %s GROUP BY province ORDER BY total_perf DESC LIMIT 10
    """, (pat,))
    provinces = [row_to_float(r) for r in cur.fetchall()]

    # 行业匹配
    cur.execute("""
        SELECT DISTINCT industry, SUM(performance) as total_perf
        FROM data_380 WHERE industry LIKE %s GROUP BY industry ORDER BY total_perf DESC LIMIT 10
    """, (pat,))
    industries = [row_to_float(r) for r in cur.fetchall()]

    conn.close()
    return {"projects": projects, "provinces": provinces, "industries": industries}

@app.get("/api/380/topProjects")
def api_380_top_projects(limit: int = 20, industry: str = "", keyword: str = ""):
    conn = get_conn()
    cur = conn.cursor()
    base_where = "WHERE 1=1"
    params = []
    if industry:
        base_where += " AND industry=%s"
        params.append(industry)
    if keyword:
        base_where += " AND (project_name LIKE %s OR settle_name LIKE %s)"
        pat = f"%{keyword}%"
        params.extend([pat, pat])
    cur.execute(f"""
        SELECT settle_name, province, industry, project_name,
               SUM(performance) as total_perf, SUM(operating_profit) as total_op,
               SUM(payment_amount) as total_pay
        FROM data_380 {base_where}
        GROUP BY settle_name, province, industry, project_name
        ORDER BY total_perf DESC LIMIT %s
    """, params + [limit])
    rows = cur.fetchall()
    conn.close()
    return {"data": [row_to_float(r) for r in rows]}

@app.get("/api/380/industries")
def api_380_industries():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT industry FROM data_380 ORDER BY industry")
    rows = [r['industry'] for r in cur.fetchall()]
    conn.close()
    return {"industries": rows}

@app.get("/api/380/profitVsRevenue")
def api_380_profit_vs_revenue(industry: str = ""):
    conn = get_conn()
    cur = conn.cursor()
    if industry:
        cur.execute(f"""
            SELECT DATE_FORMAT(report_date,'%Y-%m') as month,
                   SUM(sales_revenue) as revenue, SUM(operating_profit) as profit,
                   SUM(market_expense) as market_exp, SUM(finance_expense) as finance_exp
            FROM data_380 WHERE industry='{industry}'
            GROUP BY DATE_FORMAT(report_date,'%Y-%m') ORDER BY month ASC
        """)
    else:
        cur.execute("""
            SELECT DATE_FORMAT(report_date,'%Y-%m') as month,
                   SUM(sales_revenue) as revenue, SUM(operating_profit) as profit,
                   SUM(market_expense) as market_exp, SUM(finance_expense) as finance_exp
            FROM data_380 GROUP BY DATE_FORMAT(report_date,'%Y-%m') ORDER BY month ASC
        """)
    rows = cur.fetchall()
    conn.close()
    return {"data": [row_to_float(r) for r in rows]}

# ────────── 健康检查 ──────────
@app.get("/api/health")
def api_health():
    try:
        conn = get_conn()
        conn.close()
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

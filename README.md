# 380 Platform Data Visualization & Anomaly Detection System

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/MySQL-5.7+-orange.svg" alt="MySQL">
  <img src="https://img.shields.io/badge/Chart.js-4.0+-ff6384.svg" alt="Chart.js">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License">
</p>

<p align="center">
  <b>中文</b> | <a href="README_EN.md">English</a>
</p>

---

## 📖 项目简介

一个基于 **FastAPI + MySQL + 原生 HTML/JS** 的企业级数据可视化与智能异常告警系统。支持多维度数据分析、实时异常检测、用户认证管理和告警历史追踪。

### ✨ 核心特性

- 📊 **多维度可视化** - 行业分布、省区排行、月度趋势、收入利润对比
- 🔍 **智能异常检测** - 基于 3σ 原则和环比波动的自动异常识别
- 👤 **用户认证系统** - 完整的注册/登录/Token 验证机制
- 🔔 **告警历史管理** - 检测记录持久化，支持搜索和筛选
- 🔎 **全局搜索** - 支持项目、省份、行业多维度搜索
- 📱 **响应式设计** - 适配桌面端，白色主题 UI

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- MySQL 5.7+
- 现代浏览器（Chrome/Firefox/Edge）

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/yourusername/380-platform-visualization.git
cd 380-platform-visualization
```

2. **安装依赖**

```bash
pip install fastapi uvicorn pymysql pandas openpyxl
```

3. **配置数据库**

修改 `backend/main.py` 中的数据库配置：

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "your_username",
    "password": "your_password",
    "database": "your_database",
    "charset": "utf8mb4",
}
```

4. **启动服务**

**Windows:**
```bash
QUICK_START.bat
```

**Linux/Mac:**
```bash
python backend/main.py
# 新终端
python -m http.server 8765
```

5. **访问系统**

打开浏览器访问：`http://localhost:8765/dashboard.html`

---

## 📁 项目结构

```
380-platform-visualization/
├── backend/
│   └── main.py                 # FastAPI 后端服务
├── dashboard.html              # 主前端应用
├── 380平台可视化系统.html       # 单文件独立版本
├── import_xlsx.py              # Excel 数据导入脚本
├── start_servers.py            # 一键启动脚本
├── QUICK_START.bat             # Windows 快速启动
├── README.md                   # 项目说明（本文件）
├── LICENSE                     # MIT 开源协议
└── .gitignore                  # Git 忽略配置
```

---

## 🔧 数据导入

系统支持从 Excel 文件导入业务数据：

```bash
python import_xlsx.py
```

**数据格式要求：**

Excel 文件需包含以下列：
- 结算编码、结算客户、省区平台、城市
- 行业、项目简称、日期
- 业绩量、销售收入、经营利润等财务指标

导入后会自动创建 `data_380` 数据表。

---

## 📊 功能模块

### 1. 数据概览
- 核心 KPI 指标卡片
- 行业分布统计（柱状图+饼图）
- 省区 TOP10 排行
- 月度趋势分析
- 收入 vs 利润对比

### 2. 异常告警
- 自动异常检测（业绩/收入/利润）
- 告警分级（高/中/低）
- 告警历史记录
- 行业筛选和关键词搜索

### 3. 全局搜索
- 顶部导航栏快捷搜索
- 支持项目、省份、行业搜索
- 实时下拉结果展示

---

## 🔬 异常检测算法

系统采用多规则异常检测引擎：

| 检测规则 | 严重级别 | 说明 |
|---------|---------|------|
| 绝对值异常 | 🔴 High | 偏离行业均值超过 3 倍标准差 |
| 环比波动 | 🟡 Medium | 环比变化超过 ±50% |
| 业绩骤降 | 🔴 High | 当前值<100 且上月>1000 |

---

## 🛠️ API 接口

### 认证接口
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/me` - 获取当前用户

### 数据接口
- `GET /api/380/overview` - 数据概览
- `GET /api/380/byIndustry` - 按行业统计
- `GET /api/380/byProvince` - 按省区统计
- `GET /api/380/trend` - 月度趋势
- `GET /api/380/search` - 全局搜索

### 告警接口
- `GET /api/alert/detect` - 执行异常检测
- `GET /api/alert/history` - 告警历史
- `DELETE /api/alert/history/{id}` - 删除记录
- `GET /api/alert/stats` - 告警统计

完整 API 文档访问：`http://localhost:8000/docs`

---

## 🎨 技术栈

| 层级 | 技术 |
|-----|------|
| 后端 | FastAPI, PyMySQL |
| 前端 | HTML5, CSS3, Vanilla JS |
| 图表 | Chart.js |
| 数据库 | MySQL |
| 部署 | Uvicorn, Python HTTP Server |

---

## 📝 配置说明

### 数据库配置

在 `backend/main.py` 中修改：

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "your_password",
    "database": "stock_db",
    "charset": "utf8mb4",
}
```

### 前端 API 地址

如需修改后端地址，编辑 `dashboard.html`：

```javascript
const API_BASE = 'http://localhost:8000';
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Python Web 框架
- [Chart.js](https://www.chartjs.org/) - 强大的 JavaScript 图表库
- [PyMySQL](https://github.com/PyMySQL/PyMySQL) - Python MySQL 客户端

---

## 📧 联系

如有问题或建议，欢迎提交 Issue 或联系维护者。

---

<p align="center">
  Made with ❤️ by Open Source Community
</p>

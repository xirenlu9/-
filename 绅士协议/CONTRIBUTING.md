# 贡献指南

感谢你对本项目的关注！我们欢迎各种形式的贡献。

## 🚀 如何贡献

### 报告问题

如果你发现了 bug 或有功能建议：

1. 先搜索现有 Issue，避免重复
2. 创建新 Issue，详细描述问题
3. 提供复现步骤和环境信息

### 提交代码

1. **Fork 仓库**
   ```bash
   git clone https://github.com/yourusername/380-platform-visualization.git
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/bug-description
   ```

3. **提交更改**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

   提交信息规范：
   - `feat:` 新功能
   - `fix:` 修复 bug
   - `docs:` 文档更新
   - `style:` 代码格式调整
   - `refactor:` 重构
   - `test:` 测试相关
   - `chore:` 构建/工具相关

4. **推送并创建 PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📋 代码规范

### Python

- 遵循 PEP 8 规范
- 使用类型注解
- 函数和类添加 docstring

```python
def detect_anomalies(data: list[dict]) -> list[dict]:
    """
    检测数据中的异常值
    
    Args:
        data: 输入数据列表
        
    Returns:
        异常数据列表
    """
    pass
```

### JavaScript

- 使用 ES6+ 语法
- 变量使用 camelCase
- 常量使用 UPPER_SNAKE_CASE

```javascript
const API_BASE = 'http://localhost:8000';

async function fetchData(endpoint) {
    const response = await fetch(`${API_BASE}${endpoint}`);
    return response.json();
}
```

### CSS

- 使用 BEM 命名规范
- 避免使用 !important

```css
.block { }
.block__element { }
.block--modifier { }
```

## 🧪 测试

提交 PR 前请确保：

- [ ] 代码可以正常运行
- [ ] 没有引入新的警告
- [ ] 相关功能已测试
- [ ] 文档已更新（如需要）

## 📞 联系方式

如有疑问，欢迎通过 Issue 讨论。

再次感谢你的贡献！

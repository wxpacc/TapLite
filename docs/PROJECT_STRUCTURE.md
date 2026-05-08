# 项目结构说明

TapLite 采用稳妥的轻量结构，保留根目录入口和 `taplite/` 包，不引入 `src/` 布局。

```text
TapLite/
├─ taplite/      # 应用源码
├─ tests/        # 自动化测试
├─ scripts/      # 构建和清理脚本
├─ docs/         # 项目说明文档
├─ releases/     # 用户可直接使用的发布成品
├─ .github/      # GitHub 模板和 CI
├─ main.py       # 开发运行入口
├─ pyproject.toml
└─ README.md
```

`dist/`、`build/`、`*.spec`、缓存目录和 `settings.json` 都是本地生成内容，不作为源码结构的一部分。

构建发布文件时运行：

```powershell
.\scripts\build.ps1
```

清理临时生成物时运行：

```powershell
.\scripts\clean.ps1
```

# 项目结构说明

TapLite 保持轻量的根入口结构，不引入 `src/` 布局，降低打包和运行复杂度。

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

`build/`、`dist/`、`*.spec`、缓存目录、根目录旧版 `settings.json` 和 `data/` 都是本地生成内容，不作为源码结构的一部分。`releases/TapLite.exe` 是面向用户的发布成品。

运行时数据统一保存到软件所在目录的 `data/settings.json`。打包为 exe 后，这个目录位于 `TapLite.exe` 旁边；源码运行时位于工程根目录。删除整个项目/软件文件夹即可清除全部运行数据。

构建发布文件时运行：

```powershell
.\scripts\build.ps1
```

清理临时生成物时运行：

```powershell
.\scripts\clean.ps1
```

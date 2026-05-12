# 项目结构说明

TapLite 保持轻量的根目录结构，不引入 `src/` 布局，降低打包和运行复杂度。

```text
TapLite/
├─ assets/       # 项目图标等静态资源
├─ taplite/      # 应用源码
├─ tests/        # 自动化测试
├─ scripts/      # 构建和清理脚本
├─ docs/         # 项目说明文档
├─ releases/     # 面向用户的发布成品
├─ .github/      # GitHub 模板和 CI
├─ main.py       # 开发运行入口
├─ pyproject.toml
└─ README.md
```

说明：

- `assets/TapLite.ico` 是项目图标资源，开发运行、系统托盘和打包流程都会使用它。
- `releases/TapLite.exe` 是面向用户的发布产物，不作为源码结构的一部分。
- `build/`、`dist/`、`*.spec`、缓存目录、根目录旧版 `settings.json` 和 `data/` 都属于本地生成内容。
- 运行时数据统一保存在软件所在目录的 `data/settings.json`。
- 打包为 `exe` 后，`data/` 位于 `TapLite.exe` 同级目录；源码运行时则位于项目根目录。
- 项目不会额外写入注册表常驻项、系统服务或其他隐藏残留；如果要卸载并清除数据，直接删除 TapLite 文件夹即可。

构建发布文件：

```powershell
.\scripts\build.ps1
```

清理临时生成物：

```powershell
.\scripts\clean.ps1
```

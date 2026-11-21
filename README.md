# 铺掌柜 ShopKeeper

零售进销存管理系统 · 扫码收银 · 库存管家

基于 Python + Streamlit + SQLite 的本地零售管理工具。面向小商店、便利店与个体经营者，覆盖扫码销售、扫码入库、退货、进货单、会员、供应商、库存盘点、销售分析与数据备份。所有数据保存在本机，不依赖网络服务。

## 功能概览

| 模块 | 主要能力 |
|------|----------|
| 数据看板 | 销售额/利润/库存健康度一览，低库存与临期商品预警 |
| 销售模式 | 条码扫码、购物车合并同类、库存预占校验、事务性扣减结算 |
| 入库模式 | 已有商品追加库存、新商品自动登记、拼音码生成、生产日期与保质期计算 |
| 退货管理 | 扫码退货、库存回滚、退款金额统计、历史追踪 |
| 商品管理 | 搜索/筛选/排序、批量编辑、进售价与警戒库存维护 |
| 进货管理 | 进货单检索、临期高亮、售空标记、保质期筛选 |
| 会员管理 | 会员档案、积分累计与兑换 |
| 供应商管理 | 供应商档案与联系方式维护 |
| 库存盘点 | 盘点差异确认、库存校正 |
| 批量操作 | 批量入库、批量调价、Excel 批量导入 |
| 打印标签 | 商品价签 HTML 生成与打印预览 |
| 数据备份 | 自动/手动备份、历史备份恢复（二次确认） |

## 目录结构

```
ShopKeeper/
├── launcher.py            # 免安装版启动器（数据目录、端口、浏览器）
├── streamlit_app.py       # 应用入口与侧边栏导航
├── config.py              # 品牌、路径、业务阈值统一配置
├── build.py               # 一键打包脚本
├── database/（或 data/database/） # 建表与 Excel 迁移
├── models/                # 数据访问层
├── services/              # 业务逻辑层
├── ui/                    # 页面与通用组件
├── data/                  # 运行数据（数据库、备份、日志、种子 Excel）
└── dist/                  # 打包产物（构建后生成）
```

## 源码运行

```bash
# 1. 进入项目目录
cd ShopKeeper

# 2. 安装依赖（已有 .venv 可跳过）
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. 启动
.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

首次启动会自动建库；若数据库为空且存在 `data/商品资料.xlsx`（或根目录同名文件），会自动迁移商品主数据。

## 打包为免安装程序

```bash
.venv\Scripts\python.exe build.py             # 目录版（推荐）+ UPX 压缩 + zip 分发包
.venv\Scripts\python.exe build.py --onefile   # 单文件 exe（启动较慢）
.venv\Scripts\python.exe build.py --no-upx    # 关闭 UPX 压缩
.venv\Scripts\python.exe build.py --check     # 只做环境自检
```

程序图标取自项目根目录的 `icon.ico`（缺失时自动回退生成备用图标）。UPX 默认使用 `H:\UPX\upx.exe`，可用 `--upx-dir` 指定其他目录。PyInstaller 6 生成的 exe 默认开启 CFG，UPX 5 需以 `--force` 压缩（会关闭 CFG 标记）；压缩后的二进制可能被部分杀毒软件误报，如需规避请使用 `--no-upx` 重新打包。

产物位于 `dist/ShopKeeper_<时间戳>/`：目录版为其中的 `ShopKeeper/ShopKeeper.exe`，单文件版为其中的 `ShopKeeper.exe`。每次构建另生成统一名称的 zip 分发包 `dist/ShopKeeper_v4.1.0_win_x64.zip`，始终对应最近一次构建。

**数据与程序分离**：exe 同级 `data/` 保存数据库、备份和日志。升级时替换程序文件即可，`data/` 不受影响。扫码枪请设置为「自动回车」模式。

## 配置说明

所有可调项集中在 `config.py`，包括品牌名称、业务阈值（库存预警、保质期预警）、默认分页与日期范围。打包运行时可通过环境变量覆盖数据位置：

- `SHOPKEEPER_DATA_DIR`：数据根目录
- `SHOPKEEPER_DB_PATH`：数据库文件完整路径
- `SHOPKEEPER_LOG_DIR` / `SHOPKEEPER_BACKUP_DIR`：日志与备份目录

## 许可证

MIT

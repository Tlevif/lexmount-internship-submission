# 开发流程与工具使用说明

## 1. 项目流程

目标是聚合北京、上海、广州、深圳、杭州的企业官网计算机技术实习岗位。开发流程为：明确收录范围 → 发现官网入口 → 读取列表 → 动态交互与翻页 → 提取详情 → 清洗分类 → 入库 → 页面展示。

| 步骤 | 使用工具 | 具体操作与产出 |
| --- | --- | --- |
| 明确范围 | 人工、Codex | 人工确定城市、实习类型和计算机技术要求；Codex协助实现适配程序与数据处理代码。 |
| 发现招聘入口 | Lexmount WebFetch | 对公开官网招聘页执行extract，识别招聘列表及详情链接，记录官方来源。 |
| 检查页面结构 | Lexmount WebFetch | 用dump-dom读取DOM，再用返回的dom_id继续提取；判断列表是否已加载、字段在哪里。 |
| 处理动态网页 | Lexmount Cloud Browser | 创建临时云浏览器会话、打开招聘入口、等待页面渲染，以snapshot检查实际岗位列表。 |
| 筛选与分页 | Lexmount Cloud Browser | 根据当前快照选择控件，设置实习、城市等条件，点击下一页；每次操作后检查筛选状态和岗位标识，避免重复读取同一页。 |
| 提取职责与要求 | WebFetch、Cloud Browser、Python | 静态详情用WebFetch提取；动态详情用云浏览器打开后读取；对公开岗位接口用Python读取结构化字段。按原文栏目拆分职责与要求。 |
| 清洗、筛选与分类 | Python | 统一城市和实习类型，按稳定岗位标识去重；结合岗位名称、实际任务和任职要求判断技术方向，生成大方向与子方向。 |
| 统一存储 | Python、SQLite | 保存JSONL快照，写入SQLite；相同岗位再次采集时更新记录。未公布的原站发布日期保持为空。 |
| 检索与导出 | FastAPI、HTML/CSS/JavaScript | 提供关键词、企业、城市、父子方向筛选、岗位详情、页码跳转和CSV导出。 |

## 2. Lexmount工具如何分工

WebFetch适合不需要持续交互的公开网页读取，主要用于入口发现、正文提取与DOM复用。Cloud Browser用于需要渲染、点击、填写、翻页或保持浏览器状态的页面。先检查WebFetch得到的内容；当只有页面壳、缺少岗位列表或必须操作控件时，再切换到Cloud Browser。

本项目中，百川招聘列表通过Cloud Browser核对实习岗位，WebFetch用于入口与正文读取；腾讯列表通过浏览器分页并核对岗位标识；华为岗位需要选择具体招聘方向后再读取详情。不同企业的配置由源码中的configs/sites管理。

## 3. 准备Lexmount CLI

以下命令使用Windows PowerShell。先安装Lexmount技能及其CLI，将两个环境变量改为本机实际路径：

```powershell
$env:LEXMOUNT_WEBFETCH_CLI = 'C:\实际安装目录\lexmount-webfetch\bin\webfetch-cli.exe'
$env:LEXMOUNT_BROWSER_CLI = 'C:\实际安装目录\lexmount-browser\bin\browser-cli.exe'
$webfetchCli = $env:LEXMOUNT_WEBFETCH_CLI
$browserCli = $env:LEXMOUNT_BROWSER_CLI
& $webfetchCli version
& $webfetchCli doctor --json
& $browserCli doctor
```

没有登录凭据时，执行WebFetch的auth login --open或Cloud Browser的auth login，并在浏览器中完成授权。Cloud Browser的doctor输出应包含ready_for_browser_actions为true。凭据由工具管理，不写入源码。

## 4. WebFetch：读取招聘入口和详情

把careerUrl替换为岗位数据中的官方source_url。对同一份页面继续分析时，使用本次dump-dom实际返回的DOM ID。

```powershell
$careerUrl = 'https://需要读取的官方招聘页面'
& $webfetchCli extract --url $careerUrl
& $webfetchCli dump-dom --url $careerUrl --format json
& $webfetchCli extract --dom-id '<本次返回的DOM ID>' --format text
```

extract用于快速读取标题、正文和链接；dump-dom用于获取页面结构和可复用快照。检查输出是否含真实岗位卡和正文，不能仅凭请求成功就认定内容已提取完整。静态详情页可继续使用extract；只有页面壳时转入下一步。

## 5. Cloud Browser：动态列表、筛选和分页

先创建会话，并从响应中复制会话ID。选择器应来自本次snapshot显示的页面；下方button.next-page只是操作位置示例，需替换为目标网站的实际选择器。

```powershell
& $browserCli session create
$cloudSessionId = '<本次返回的会话ID>'
& $browserCli action open-url --session-id $cloudSessionId --url $careerUrl
& $browserCli action snapshot --session-id $cloudSessionId
& $browserCli action wait-text --session-id $cloudSessionId --text '实习'
& $browserCli action click --session-id $cloudSessionId --selector 'button.next-page'
& $browserCli action snapshot --session-id $cloudSessionId
```

实际采集时，先从快照定位实习及城市筛选控件；需要填写时用action fill，点击后用wait-selector或wait-text等待目标内容，再用snapshot读取新页面。逐页比较页码、岗位链接或稳定标识，确认页面确实变化。打开详情后按对应栏目读取职责和要求，再返回列表继续处理。

点击产生新标签页时，先执行session targets匹配详情URL。只有本机action --help实际支持--target-id时，才使用该参数指定目标页；不支持时应升级CLI后再做多标签采集。需要截图核对时可执行action screenshot。完成采集后关闭临时会话：

```powershell
& $browserCli action screenshot --session-id $cloudSessionId --path '招聘页面.png'
& $browserCli session close --session-id $cloudSessionId
```

## 6. 详情提取、去重与分类

collector/detail_sections.py负责处理职责、要求等栏目；collector和各站点配置负责列表及详情适配。Python读取公开岗位接口时保留对应官网链接，将接口字段转换为统一岗位结构。

app/core.py进行字段标准化，app/classification.py与app/taxonomy.py判断计算机技术方向，app/category_tree.py生成两级标签。依据实际任务和要求区分技术岗位与非技术岗位。大模型下包括基模、预训练、后训练、AI Infra、推理、数据、评测、多模态、Agent算法、应用算法、应用开发、综合算法。

按企业与稳定岗位标识或详情链接去重，JSONL只按换行符LF分隔记录。当前数据共3,095条岗位、32家企业；每条均包含职责与任职要求。CSV适合表格查看，JSONL保留完整字段及分类信息。岗位是否仍开放，以官网为准。

## 7. 运行源代码

完整提交包解压后，进入04_源代码目录。单独下载源代码ZIP时，进入其解压后的根目录。Python版本为3.11或以上。

```powershell
python -m pip install -r requirements.txt
$env:DEMO_READ_ONLY = '1'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

在浏览器打开http://127.0.0.1:8000/。首次启动从data/jobs.jsonl载入岗位，生成本地SQLite数据库。浏览已有快照不需要Lexmount账号。app、frontend、collector、discovery分别对应接口、界面、采集和入口发现；scripts包含采集与统一入库脚本。

website目录保存公开材料页的HTML、CSS与JavaScript。该静态版本引用在线岗位数据和材料，可在website目录执行python -m http.server 8001后访问http://127.0.0.1:8001/。

## 8. 重新采集

配置两个Lexmount CLI环境变量并完成认证。取消只读环境变量后，可使用已核验的站点配置执行采集：

```powershell
Remove-Item Env:DEMO_READ_ONLY -ErrorAction SilentlyContinue
python -X utf8 -m scripts.collect_jobs --company '字节跳动'
```

configs/sites中的verified_for_collection控制配置是否可以采集。重新采集后需核对当前官网结构、分页和字段完整性，再更新快照。采集会实际调用Lexmount云端服务；本次材料整理复用既有完整岗位快照。

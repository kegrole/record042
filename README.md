# csvinject

CSV 公式注入检测器。只使用 Python 标准库，无任何第三方依赖。

从数据库导出的 CSV 用 Excel 等表格软件双击打开时，以 `=` 等字符开头的
文本会被当作公式执行；同一格里甚至可以用制表符塞进多段公式。本工具按
RFC 4180 解析 CSV，逐字段判定是否会被表格软件当公式执行，输出 JSON
报告与清洗后的安全 CSV。

## 用法

```sh
python -m csvinject.cli --csv demo/export.csv --out out/report.json --safe out/safe.csv
```

跑完在 stdout 打印一行摘要（字段总数、可注入数、安全数、公式条数），
例如：`cells=20 injectable=12 safe=8 formulas=14`。

## CSV 解析规则（RFC 4180）

- 字段可以用双引号包起来；包起来的字段里逗号、制表符、回车、换行都算普通字符。
- 字段内的双引号写成两个（`""`）。
- 行尾 LF 与 CRLF 都能读。
- 解析出的字段值就是原始值：不做 strip，前导空格与控制字符全部保留。
- 表格里每一个字段都参与判定，第一行（表头）也不例外。

## 片段切分与数值例外

判定一个字段时，先按 TAB、CR、LF 切成若干片段（这三个字符只是分隔符，
不算内容），再逐个片段判定：

1. 去掉片段前导的控制字符与空格（码位 0x00 到 0x20）。
2. 片段为空 → 安全。
3. 去掉前导空白后整体是一个十进制数或科学计数法的数（可带正负号，
   如 `-12.3`、`-1.2E+3`）→ 安全。
4. 否则看片段第一个字符，是 `=`、`+`、`-`、`@` 之一 → 公式片段，
   该字符就是触发字符。
5. 其余 → 安全。

注意 `-1+1` 不是数（含运算符），是公式片段。一个字段里公式片段的条数
就是它的公式条数；整字段没有公式片段才判安全。CSV 的双引号只是语法，
剥掉引号后以 `=` 开头的文本照样判可注入。

## DDE 令牌表

大小写不敏感，从上往下取第一个命中的令牌，报告里写右列的规范名：

| 令牌 | 报告名 |
| --- | --- |
| `cmd|` | `cmd` |
| `mshta` | `mshta` |
| `powershell` | `powershell` |
| `rundll32` | `rundll32` |
| `regsvr32` | `regsvr32` |
| `wscript` | `wscript` |
| `cscript` | `cscript` |
| `hyperlink(` | `HYPERLINK` |
| `importxml(` | `IMPORTXML` |
| `webservice(` | `WEBSERVICE` |
| `iexec(` | `IEXEC` |

## 形态分类（按优先级）

1. `dde`：字段里任何公式片段命中 DDE 令牌。
2. `multi_formula`：公式片段两条或以上。
3. `formula`：正好一条公式片段。
4. `safe`：没有公式片段。

## 清洗规则与 CSV 输出

- 字段里每个被判为公式的片段，在它的触发字符前面插一个单引号；其余
  字符一个字节都不动，片段前导的空格和控制字符留在引号前面。
- 没有公式片段的字段原样保留。
- 清洗后重新按 CSV 规则输出：字段里只要出现逗号、双引号、CR、LF、TAB
  之一，整个字段用双引号包起来，里面的双引号写成两个；字段之间用逗号，
  记录之间用 LF，文件末尾有一个 LF。

## 报告格式

顶层三个键：`cells`、`findings`、`summary`。

- `cells`：每个字段一条，含 `cell_ref`（列字母加行号，列从 A 起、
  行号从 1 起）、`raw_value`（可打印形式：反斜杠写成两个反斜杠、
  制表符 `\t`、回车 `\r`、换行 `\n`、其余控制字符 `\xNN` 两位
  小写十六进制）、`verdict`（`injectable` / `safe`）、`formula_count`、
  `kind`（`safe` / `formula` / `multi_formula` / `dde`）、`trigger`
  （第一个公式片段触发字符的两位小写十六进制码点，安全字段为 null）、
  `dde_token`（命中的令牌名，未命中为 null）、`sanitized`（清洗后的值）。
- `findings`：每个问题一条，含 `rule`、`cell_ref`、`detail`。命中
  DDE 令牌的字段记一条 `dde`，一个字段两条以上公式片段记一条
  `multi_formula`，同一字段两种都命中就记两条。
- `summary`：`cells`（字段总数）、`injectable`、`safe`、`formulas`
  （所有字段公式条数之和）、`findings`（问题条数）、`by_rule`
  （规则 id 到条数的映射）。

同一份输入跑两次，输出逐字节一致。

## 项目结构

- `csvinject/csvparse.py` — RFC 4180 解析与序列化
- `csvinject/detect.py` — 片段切分、数值例外、公式片段判定
- `csvinject/classify.py` — 四种形态的优先级分类
- `csvinject/dde.py` — DDE 令牌表与匹配
- `csvinject/escape.py` — raw_value 可打印转义与清洗
- `csvinject/report.py` — 报告（cells / findings / summary）构建
- `csvinject/cli.py` — 命令行入口
- `csvinject/__main__.py` — `python -m csvinject` 入口
- `demo/export.csv` — 演示数据（含真实 TAB/CR 控制字符）
- `tests/test_csvinject.py` — 覆盖全部判定口径的 unittest

## 测试

```sh
cd tests && python -m unittest test_csvinject -v
```

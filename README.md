# 六级词汇 · 拼写记忆

把三份 PDF 里的**词表**做成了一个可以每天练的小网页：看中文（或听发音）拼出英文，选中「认识 / 模糊 / 不认识」三档自评，系统自动安排下次复习。

纯静态、无后端、无第三方依赖：打开 `index.html` 就能用，进度存在浏览器本地。

- 词库：**1078 条**
  - 六级考前冲刺 600 词（含音标、词性、释义、词组，按原 PDF 的「第一天…第十天」分组）
  - 六级高频同义替换 280 组（通用类 / 经济类，如 `variety = diversity`）
  - 四六级翻译重点词汇 198 条（动作 / 政治 / 经济 / 科技 / 生活 / 环保 / 地理）
- 学习模式：看中文拼写、听发音拼写（浏览器自带英文语音）
- 判分：忽略大小写、空格、标点、连字符；差 1–2 个字母算「差一点点」
- 复习：认识 → 间隔翻倍（1/2/4/7/15/30 天）；模糊 → 半天后再练；不认识 → 本次稍后重来 + 进错词本
- 错词本：单独列表、一键重刷，连续掌握后自动移出
- 其他：今日进度环、连续天数、每日目标（10/20/30/50/100）、词库搜索、深浅色跟随系统、进度导出/导入
- 手机端可按「添加到主屏幕」，有独立图标和全屏效果

## 在线使用

部署到 GitHub Pages 后地址：

```
https://mouseking77.github.io/cet6-vocab/
```

手机打开这个地址即可；Chrome / 夸克 / Safari 菜单里的「添加到主屏幕」可以装成图标。

## 本地使用

- 直接双击 `index.html`（或拖进浏览器）即可，无需安装。
- 需要局域网给手机试：在仓库目录跑 `python -m http.server 8000`，手机访问 `http://<电脑IP>:8000/`。

## 目录结构

```
.
├── index.html            # 构建产物：单文件应用，GitHub Pages 直接服务
├── manifest.webmanifest  # 添加到主屏幕用的应用信息
├── icon-192.png
├── icon-512.png
├── .nojekyll             # 让 Pages 不要走 Jekyll
└── src/
    ├── app_template.html # 页面模板（CSS + JS），含 __DATA__ 占位符
    ├── data.json         # 词库数据（由 PDF 文本解析而来）
    ├── build.py          # data.json + 模板 → ../index.html
    ├── build_data.py     # texts/*.txt → data.json
    ├── extract_texts.py  # pdfs/*.pdf → texts/*.txt
    ├── pdftext.py        # 零依赖 PDF 文本抽取（Type0 字体 + ToUnicode）
    ├── make_icons.py     # 生成图标
    ├── test_app.js       # 逻辑自测（41 项，Node 直接跑）
    └── texts/            # 三份 PDF 抽出的纯文本（已入库，方便复现）
```

## 改词库 / 重新构建

PDF 受版权限制**没有**放进仓库。要重新生成：

1. 把三份 PDF 放进 `pdfs/`（文件名不必完全一致，脚本按关键词匹配：`600`、`同义替换`、`翻译重点词汇`）。
2. 依次运行：

```bash
python src/extract_texts.py     # PDF → src/texts/*.txt
python src/build_data.py        # 文本 → src/data.json（会打印条数，应为 600 / 280 / 198）
python src/build.py             # data.json + 模板 → index.html
node src/test_app.js            # 41 项逻辑自测，最后一行 FAIL=0 即通过
```

只想调整界面（颜色、文案、交互）时，改 `src/app_template.html` 后跑 `python src/build.py` 即可，**不用**碰 PDF。

## 部署到 GitHub Pages

仓库：<https://github.com/mouseking77/cet6-vocab>

### 方式 A：网页上传（不用装 git，推荐）

1. 打开仓库页 <https://github.com/mouseking77/cet6-vocab>。
2. 点中间的 **uploading an existing file**（或 `Add file → Upload files`）。
3. 从本机 `cet6-vocab` 目录里拖进这些（**`index.html` 必须在仓库根目录**，不能放进子文件夹）：
   - `index.html`
   - `manifest.webmanifest`
   - `icon-192.png`、`icon-512.png`
   - `README.md`
   - `src/` 整个文件夹（想保留构建脚本再传；只上线的话可以不传）
4. 页面下方 `Commit changes`。
5. `Settings` → 左侧 `Pages` → `Source` 选 `Deploy from a branch`，分支 `main`、目录 `/ (root)`，`Save`。
6. 等 1–2 分钟，站点地址：<https://mouseking77.github.io/cet6-vocab/>

> `.nojekyll`、`.gitignore` 是隐藏文件，网页上传时不容易选中；不传也不影响访问（本项目没有以下划线开头的文件，Jekyll 不会出错）。

### 方式 B：命令行（本机仓库已初始化好）

本机 `cet6-vocab` 目录已经 `git init`、提交完成、remote 指向本仓库，只差认证后推送：

```powershell
cd D:\English_learning\cet6-vocab
git push -u origin main
```

GitHub 不接受账号密码，密码处要填 **Personal Access Token**：
`GitHub → 头像 → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token`，勾选 `repo`，生成后复制（只显示一次），在 git 提示 `Password` 时粘贴。

如果装了 GitHub Desktop 或 VS Code，登录账号后直接「Push」更省事。推送后同样去 `Settings → Pages` 开一次。

### 手机打开

浏览器输入 <https://mouseking77.github.io/cet6-vocab/>（夸克/Chrome/Safari 都行，是正常网页，输入框可正常输入）。想更像 App：浏览器菜单里「添加到主屏幕」。

## 说明

- 进度保存在**当前浏览器**的 localStorage 里，换设备 / 清缓存会丢；设置页可「导出进度」备份成 JSON，再到别的设备「导入进度」。
- 发音用系统语音（`speechSynthesis`），个别设备需要先下载英文语音包；不支持时会提示切回看中文。
- 词表版权归原作者（博主：梁伟考研英语）所有，本项目仅个人学习使用，请勿商用。

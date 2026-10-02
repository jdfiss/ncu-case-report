# Case Report

把每週個案資料交給 Claude Code 分析，產生繁體中文個案討論報告（Markdown、HTML、PDF）。提供本機網頁介面，可拖曳上傳、查看生成日誌及下載報告。

預設分析兩個 Case，每個 Case 包含背景、利害關係人、核心爭點、多元觀點與辯證、延伸議題、綜合建議；也可處理單一 Case。

## 使用前準備

- Python 3 與 pip；請確認終端機可執行 `python --version`。
- 已安裝並登入的 Claude Code CLI；請確認 `claude --version` 可執行，並先在終端機開啟 `claude` 完成登入與初次設定。每位隊友使用自己的帳號與使用額度。
- Chrome、Edge 或 Chromium，供報告轉成 PDF 使用。

這是本機工具。上傳檔案會存到電腦的 `input/`，生成時由 Claude Code 讀取並處理資料。

## 第一次使用（Windows）

1. 在 GitHub 按 **Code → Download ZIP**，解壓縮；或執行：

   ```powershell
   git clone https://github.com/jdfiss/ncu-case-report.git
   cd ncu-case-report
   ```
2. 在專案資料夾開啟終端機，安裝套件：

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. 雙擊 `Case Report.bat`，或執行：

   ```powershell
   python ui.py
   ```

4. 瀏覽器會自動開啟 `http://localhost:8742`。拖入本週 Case 檔案，按生成報告。
5. 完成後從網頁開啟／下載報告，或到 `output/` 取出檔案。

使用期間保留啟動程式的終端機視窗。要關閉服務，在該視窗按 Ctrl+C。

macOS／Linux 請使用對應的 Python 3 指令安裝套件及執行 `ui.py`；`.bat` 啟動器僅供 Windows 使用。

## 每週更新資料

先刪除或移走 `input/` 上週資料，再放入本週 Case。可透過網頁管理檔案，也可以直接複製到 `input/`。如有課堂筆記或組員討論紀錄，可以一起放入並使用清楚的檔名。

文字抽取支援 PDF、DOCX、PPTX、TXT、MD、CSV、XLSX／XLSM。圖片由 Claude Code 視覺讀取；掃描 PDF 的文字抽取可能為空，需要另外辨識。

生成結果使用固定檔名，重新生成會覆寫原報告；需要留存時，先另外備份：

- `output/case_report.md`：可編輯的報告原稿。
- `output/case_report.html`：排版中間檔。
- `output/case_report.pdf`：正式 PDF。
- `work/source_text.md`：從原始資料抽取的文字。

請在提交報告前核對原始資料、分析內容與 PDF 排版。介面的階段進度是依日誌關鍵字推估。

## 直接用 Claude Code

在專案資料夾開啟 `claude`，輸入 `/case-report`，也可以執行完整流程。分析規則放在 `.claude/skills/case-report/SKILL.md`。

## 常見問題

- **找不到 python**：先確認 Python 已安裝，並可從新開的終端機執行。
- **claude CLI not found in PATH**：確認 `claude --version` 可執行，安裝／設定完成後重新開啟終端機及本工具。
- **生成失敗**：先查看網頁日誌；在專案資料夾直接執行 `claude`，確認登入、帳號額度與專案權限。
- **PDF 生成失敗**：確認已安裝 Chrome／Edge。如果瀏覽器在非標準位置，可在啟動程式前設定 `CHROME_PATH` 或 `EDGE_PATH` 為瀏覽器執行檔的完整路徑。
- **8742 埠被占用**：關閉先前開啟的工具；需要換埠時修改 `ui.py` 的 `PORT`。

## 專案結構

```text
Case Report.bat                 Windows 啟動器
ui.py                           本機網頁與 Claude CLI 呼叫
requirements.txt                Python 套件
.claude/skills/case-report/      分析規則、模板、評分標準與處理腳本
input/                          本週原始資料
work/                           抽取文字
output/                         報告成果
```

## 團隊協作

此 repository 分享程式、分析規則與模板。Git 忽略 `input/` 的個案資料、`work/` 與 `output/` 的生成檔案；原始文章、討論紀錄及報告請透過團隊約定的方式分享。

修改程式或規則後提交並推送，隊友以 `git pull` 更新。用 ZIP 下載的隊友需要重新下載新版。

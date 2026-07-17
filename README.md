# Web2IPA

把線上網址或離線 HTML 網站打包成 **未簽名 IPA**，適合再交給 SideStore、AltStore、Sideloadly、Feather、TrollStore 等工具處理安裝／簽名。

## 可自訂

- App 顯示名稱、IPA 檔名、Bundle ID、版本與 Build
- App 圖示、啟動畫面圖片與背景色
- 線上網址或離線網站 ZIP
- 直向、橫向、自動旋轉
- 狀態列、返回手勢、User-Agent、螢幕休眠
- HTTP、相機、麥克風、相簿、定位權限文字
- 外部網域是否改用 Safari

## 部署到自己的 GitHub

1. Fork 或上傳整個專案到 GitHub，預設分支建議使用 `main`。
2. 到 **Settings → Actions → General**，允許 Actions 執行。
3. 到 **Settings → Pages**，Source 選擇 **GitHub Actions**。
4. 執行一次 `Deploy GitHub Pages` workflow。
5. 建立 Fine-grained personal access token：
   - Repository access：只選你的 Web2IPA 倉庫
   - Repository permissions：`Contents: Read and write`、`Actions: Read and write`
6. 開啟 Pages 網址，在頁面輸入倉庫資訊與 Token，設定 App 後按「開始打包」。
7. 到 **Actions → Build unsigned IPA → Artifacts** 下載成品。

> Token 由瀏覽器直接傳給 GitHub API，不會寫入網站或倉庫。仍建議建立專用、限單一倉庫、可隨時撤銷的 Token，且不要在公共裝置使用。

## 離線網站 ZIP 格式

```text
site.zip
├── index.html
├── style.css
├── app.js
└── images/
```

`index.html` 必須在 ZIP 根目錄。系統也會嘗試自動處理只有一層外部資料夾的 ZIP。

## 手動觸發

也可以直接把請求資料放進：

```text
requests/你的ID/config.json
requests/你的ID/icon.png
requests/你的ID/splash.png   # 選填
requests/你的ID/site.zip     # 離線模式才需要
```

然後在 Actions 手動執行 `Build unsigned IPA`，填入該 ID。

## 注意

- 輸出的 IPA 沒有 Apple 簽名，不能直接點擊安裝；側載工具通常會再簽名。
- 僅包裝你有權使用的網站與素材。
- 網站若依賴 Safari 不支援的 API、跨域限制、DRM、推播或特殊原生能力，包成 WKWebView 後不一定能正常運作。
- GitHub Pages 是公開靜態網站；不要把固定 Token 寫進 `app.js`。

# 轻衡 Web

Vue 3、Pinia 和 Vite 实现的本地单用户界面，主导航为“今日 / 记录 / 档案”。页面采用区间卡片而非趋势图，建议与追问只保留在当前浏览器会话。

```powershell
npm install
npm run dev
npm run test:unit -- --run
npm run type-check
npm run build
```

Vite 将 `/api` 代理到 `http://127.0.0.1:8001`。拍照上传使用原始二进制请求体；服务端不会保留照片。

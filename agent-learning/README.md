# 轻衡 API

FastAPI 后端负责服务端可信的热量计算、PostgreSQL 持久化、真实图片格式验证和按需 DashScope 调用。

## 配置

复制 `.env.example` 为 `.env` 并填写数据库和模型密钥。统一使用 `DATABASE_URL`；旧 `CHECKPOINT_DATABASE_URL` 仅作为临时启动兼容，不再写入示例配置。

## 数据库

启动时依次执行 `db/migrations/*.sql`，并幂等写入 275 个食物模板和 40 个 MET 活动。每个食物模板保存中心热量与误差率；照片识别只提供食物、份量和置信度，热量由服务端计算。整餐通过不确定度平方和及 8% 公共误差聚合，不直接累加所有最坏极值。旧照片记录会使用已保存的结构化组成自动重算一次，无需原图或用户确认。

API 使用服务端固定的 `local-user`，不接受客户端用户 ID、热量汇总或来源正文。

## 运行与测试

```powershell
uv sync
uv run python -m app.main
uv run python -m unittest discover -s tests -v
```

服务仅监听 `127.0.0.1:8001`。照片接口接收原始二进制请求体，餐次通过查询参数提交；请求扩展名和 Content-Type 不参与真实格式判定。JPEG、PNG、WebP 以及微信常见的双帧 MPO/JPEG 容器会经过文件头、帧数、总像素和完整解码校验，最终只在内存中重编码为单帧 JPEG。

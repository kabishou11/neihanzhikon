# 安全说明

## API Key 泄露处理

如果您的 API Key 曾经提交到 git 历史中，请立即：

1. **撤销旧的 API Key**
   - 登录 ModelScope 控制台
   - 删除泄露的 API Key
   - 生成新的 API Key

2. **更新本地配置**
   ```bash
   # 编辑 .env 文件
   MODELSCOPE_API_KEY=ms-new-api-key
   ```

3. **清理 git 历史**（可选）
   ```bash
   # 使用 BFG Repo-Cleaner（推荐）
   java -jar bfg.jar --delete-files config.yaml
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   
   # 强制推送
   git push origin main --force
   ```

## 最佳实践

- ✅ 使用 `.env` 文件存储敏感信息
- ✅ `.env` 已在 `.gitignore` 中，不会被提交
- ✅ 使用 `.env.example` 作为模板，不包含真实密钥
- ❌ 永远不要在代码中硬编码 API Key
- ❌ 永远不要提交 `.env` 文件到 git

## 环境变量优先级

```
环境变量 > .env 文件 > 代码默认值
```

示例：
```bash
# 临时覆盖（不修改 .env）
MODELSCOPE_API_KEY=ms-temp-key python fastapi_app.py
```

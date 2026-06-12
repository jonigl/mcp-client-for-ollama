# Atlas Cloud Provider Review

## 改动概览

- 新增 `mcp_client_for_ollama/providers.py`
  - 增加 Atlas Cloud 适配层，基于 OpenAI 兼容接口接入 `https://api.atlascloud.ai/v1`
  - 保留 Ollama 现有调用路径，按 `--host` 自动识别 Atlas Cloud
  - 增加统一的 provider 错误处理与流式响应解析
- 更新 `mcp_client_for_ollama/client.py`
  - 将底层模型客户端改为通过 provider 工厂创建
  - 为 tool follow-up 请求补充 `tool_call_id`
  - 将连接错误/模型错误文案改为 provider-aware
- 更新 `mcp_client_for_ollama/utils/connection.py`
  - 预检逻辑支持 Atlas Cloud
  - Atlas Cloud 失败时给出 API key / host / 网络方向的提示
- 新增 `tests/test_atlascloud_provider.py`
  - 覆盖 Atlas Cloud host 检测、客户端选择、流式 tool-call 合并、消息格式转换
- 更新 `README.md`
  - 新增 Atlas Cloud 接入说明
  - 插入 Atlas Cloud 图片与图片中的文案
  - 增加带 UTM 的官方链接：
    `https://www.atlascloud.ai/?utm_source=github&utm_medium=link&utm_campaign=mcp-client-for-ollama`
- 新增 `.env.example`
  - 提供 Atlas Cloud 相关环境变量示例

## 本地敏感配置

- Atlas Cloud key 不提交到仓库
- 本地建议路径：
  - `~/.config/ollmcp/atlascloud.json`
- 文件内容：

```json
{
  "apiKey": "YOUR_ATLAS_API_KEY"
}
```

## 测试计划

- 单元测试
  - 运行 Atlas Cloud provider 相关测试
  - 运行现有核心 pytest 回归
- 集成测试
  - 使用真实 Atlas Cloud key 执行模型列表、普通文本生成、流式输出
  - 执行至少一个带 tools 的往返请求，验证 tool-call 解析与 follow-up 正常

## 说明

- Atlas Cloud 适配是“最小侵入式”实现，没有重构现有 MCP/TUI 结构
- 现有默认行为仍然是 Ollama，本次仅在 `--host` 指向 Atlas Cloud 时启用新 provider

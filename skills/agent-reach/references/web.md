# 网页阅读

通用网页、RSS。

## 通用网页 (WebFetch)

优先使用 harness 自带的 WebFetch 工具（或 Exa 的 `web_fetch_exa` MCP）读取任意网页。

> **注意**: Jina Reader（`r.jina.ai`）已于 2026-07 弃用（API 不稳定），不要再使用。

## Web Reader (MCP)

```bash
# 读取网页内容 (Markdown 格式)
mcporter call 'web-reader.webReader(url: "https://example.com")'

# 保留图片
mcporter call 'web-reader.webReader(url: "https://example.com", retain_images: true)'

# 纯文本格式
mcporter call 'web-reader.webReader(url: "https://example.com", return_format: "text")'
```

**适用场景**: 需要更精确控制输出格式时使用。

## RSS (feedparser)

```python
python3 -c "
import feedparser
for e in feedparser.parse('FEED_URL').entries[:5]:
    print(f'{e.title} — {e.link}')
"
```

**适用场景**: 订阅博客、新闻源、播客等 RSS feed。

## 选择指南

| 场景 | 推荐工具 |
|-----|---------|
| 通用网页 | WebFetch / `web_fetch_exa` |
| 需要图片/格式控制 | web-reader MCP |
| RSS 订阅 | feedparser |

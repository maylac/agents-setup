# Page-change monitoring

Patterns for ongoing tracking of web page changes, content removal, and RSS-less update feeds. (Migrated from the former page-monitoring skill.)

## Monitoring service comparison

Free-tier limits and retention windows shift annually — verify at the service's pricing page before relying on a specific number. The columns below reflect a 2026 snapshot.

| Service | Free Tier | Best For | History | Alert Speed |
|---------|-----------|----------|---------|-------------|
| **Visualping** | A few daily checks (free plan tightened in recent years) | Visual changes | Standard | Minutes |
| **ChangeTower** | Yes (verify current limits) | Compliance, archiving | Multi-year on paid plans | Minutes |
| **Distill.io** | ~5 monitors with 7-day history | Element-level tracking | Limited on free tier | Seconds |
| **Wachete** | Limited | Login-protected pages | 12 months | Minutes |
| **UptimeRobot** | 50 monitors at 5-minute intervals (free SMS removed) | Uptime only | 60 days | 5-min checks |
| **changedetection.io** | Self-hosted; free | Privacy / DIY | Disk space | Configurable |
| **urlwatch** | Self-hosted; free | Cron-driven CLI | Configurable | Configurable |

## Scheduled monitoring with cron

```bash
# Edit crontab
crontab -e

# Check pages every 15 minutes
*/15 * * * * /usr/bin/python3 /path/to/monitor_script.py >> /var/log/monitor.log 2>&1

# Check critical pages every 5 minutes
*/5 * * * * /usr/bin/python3 /path/to/critical_monitor.py >> /var/log/critical.log 2>&1

# Daily summary report at 8 AM
0 8 * * * /usr/bin/python3 /path/to/daily_report.py
```

## Monitoring strategy by use case

### News monitoring

- **Pages**: breaking news sections, press release pages, government announcement pages, company newsrooms
- **Frequency**: breaking news every 5 min; press releases every 15-30 min; general news hourly
- **Archive**: archive immediately on detection; use both Wayback Machine and Archive.today; save local copy with timestamp

### Research monitoring

- **Pages**: preprint servers (arXiv, SSRN), journal tables of contents, conference proceedings, researcher profiles
- **Frequency**: daily for active topics; weekly for general monitoring
- **Tools**: Google Scholar alerts (free, built-in), Semantic Scholar alerts, RSS feeds where available, custom monitors for specific pages

### Competitive intelligence

- **Pages**: pricing pages, product pages, job postings, press releases, executive bios
- **Frequency**: pricing/products/press daily; jobs weekly
- **Legal**: don't violate terms of service; don't circumvent access controls; public pages only; don't scrape at high frequency

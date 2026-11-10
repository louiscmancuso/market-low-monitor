# Market Low Monitor

Automated stock market scanner, investment research dashboard, and daily email reports.

[Dashboard](https://louiscmancuso.github.io/market-low-monitor/) · [Setup](SETUP.md) · [Research methodology](RESEARCH_METHODOLOGY.md) · [Workflow runs](https://github.com/louiscmancuso/market-low-monitor/actions)

| View | Data | How it updates |
|---|---|---|
| SEC research | S&P 500 and Nasdaq-100 constituent directory, recent filing links and selected annual financial comparisons | Scheduled GitHub Actions attempts at 6:30 p.m. Eastern and 7:20 p.m. on weekdays. The initial report was collected locally because SEC requests from the hosted runner returned HTTP 403. |
| Screening demo | Fictional companies and prices, visibly labeled throughout | Two fixed sample sessions |
| Private reports | Personal-use price screen, qualifying-company SEC research and archived changes | Local Python scanner using an entitled source; import JSON in the browser |

The site includes sortable tables, filters, company views, session history, light/dark themes and a browser-local watchlist. GitHub Pages only receives public SEC research, constituent metadata and fictional examples.

## Cost and limitations

- **GitHub Pages and Actions** run on the existing public repository with standard runners and a small Pages artifact. Expected incremental cost is **$0/month**. [GitHub billing](https://docs.github.com/en/actions/concepts/billing-and-usage) · [Pages eligibility](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- **Wikimedia** is the free, community-maintained roster source. **SEC EDGAR** supplies free public filing metadata and XBRL facts. [Wikimedia access policy](https://www.mediawiki.org/wiki/Wikimedia_APIs/Access_policy) · [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- **Alpaca Basic** is a candidate for private delayed historical data only, subject to account entitlement and verification. The free tier does not establish public quote rights. [Plan and historical data](https://docs.alpaca.markets/us/docs/about-market-data-api) · [Historical bars](https://docs.alpaca.markets/us/reference/stockbars)
- **Google Apps Script** can send an optional public SEC digest and one demo email on the existing Google account within free MailApp quotas. It requires account authorization. [Google quotas](https://developers.google.com/apps-script/guides/services/quotas)
- No data subscription, paid AI, paid database, paid runner, custom domain or billing setup is required. The public site has no live stock prices, price-derived rankings or qualification totals. No free provider with verified rights for the requested broad public distribution was identified. The optional public SEC digest covers filing activity only and requires Google authorization.

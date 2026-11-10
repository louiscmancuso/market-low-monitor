# Research methodology

## Universe and screening

The scanner refreshes the community-maintained [S&P 500](https://en.wikipedia.org/wiki/List_of_S%26P_500_companies) and [Nasdaq-100](https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies) tables at scan time, extracts the constituent fields, and merges ticker overlaps. Distinct listed share classes are separate securities. These extracted fields retain the source's [CC BY-SA 4.0 license](https://creativecommons.org/licenses/by-sa/4.0/). Source-size checks catch common parsing failures. A current roster cannot reliably reconstruct historical index membership. SEC ticker mapping adds filing identifiers where available. A dated, SEC-sourced Nasdaq-100 identifier snapshot is available if the ticker endpoint is blocked. This snapshot does not replace current roster or filings sources.

Use the latest completed regular-session close and the lowest intraday low in the trailing 52 calendar weeks, including that session. The high is the maximum intraday high over the same dates. Daily price history is requested on a split-adjusted basis without dividend adjustment. A fresh low requires the latest session's low to be strictly below every prior low in the window. Ties do not count as fresh. A shorter available history is labeled. Market holidays and early closes follow the NYSE regular-session calendar. One day, five days, one month, three months, six months and one year are trading-session offsets of 1, 5, 21, 63, 126 and 252.

Dollar distance equals close minus low. Percentage distance equals dollar distance divided by low, multiplied by 100. A security qualifies at a dollar distance of $10 or less **or** at a percentage distance of 10% or less, including boundary values. Returns are close divided by prior close minus 1, multiplied by 100. The first report has no prior-session changes, and gaps do not masquerade as a comparison with the immediately preceding trading day.

## SEC research

The report links recent 8-K, 6-K, 10-Q, 10-K, 20-F and 40-F filings. Filing dates are inclusive and represent the date shown by EDGAR. The public report computes financial facts for up to 15 recent filers, favoring periodic reports. The private report computes them for qualifying securities when comparable facts exist. Identical tags, currency and annual periods of 350–380 days are required for year-over-year comparisons. The latest available version by filing date is selected as of the report session. Debt, cash and balance-sheet inputs use year-end values. Net income growth with a nonpositive base is omitted. Operating margin equals operating income divided by revenue. Current ratio equals current assets divided by current liabilities. These require matching period ends and positive denominators. Noncurrent debt is a limited leverage indicator and excludes current borrowings.

A company earns one point for each of revenue growth, positive net income, positive operating cash flow and operating cash flow at least as high as the prior year. Comparable revenue, net income and operating cash flow are all required. **High** requires at least three points, positive net income and positive operating cash flow. **Low** applies at zero or one point, or negative operating cash flow. Other qualifying scores are **Medium**. Incomplete data yields **Insufficient Information**. These scores prioritize follow-up research. The score is not an investment recommendation.

Company and analyst narratives, guidance revisions, upcoming earnings and market capitalization appear only when independently verified inputs are available. The current collector uses filing metadata and selected XBRL facts. It offers questions to research next and does not infer that a filing caused a stock move. It does not copy news articles, investor-relations prose or proprietary index data feeds.

## Data rights and provider comparison

| Candidate | Coverage and access | Result |
|---|---|---|
| Alpaca Basic | Historical US stock bars, multi-symbol requests, 200 historical requests/minute on Basic, delayed historical coverage subject to entitlement | Private adapter with explicit opt-in. No public distribution rights verified. |
| Twelve Data Basic | Free US coverage with 8 API credits/minute and 800/day listed; practical coverage depends on endpoint and credit use | External display and distribution permissions were not established for the intended free use. |
| Alpha Vantage free | Standard free limit of 25 requests/day on most endpoints | Per-symbol history cannot refresh the entire universe daily at that rate. Public rights were not established. |
| Stooq and unofficial Yahoo interfaces | Some historical data is accessible at no charge | Authorization for this automated public use was not verified. |

[Alpaca plan](https://docs.alpaca.markets/us/docs/about-market-data-api) · [Twelve Data pricing](https://twelvedata.com/pricing) · [Alpha Vantage support](https://www.alphavantage.co/support/) · [SEC fair access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)

# Setup and troubleshooting

## Website and SEC archive

1. In repository **Settings → Pages**, use **GitHub Actions** as the source. The repository is already public.
2. In **Actions → Market Low Monitor → Run workflow**, select `main` and keep **Refresh SEC data** checked. During the trading day the manual run uses the latest completed session with the roster observed on the day of the run.
3. Expand **Refresh SEC archive** in the job log for the number of securities verified. The deploy job reports the live URL. A failed source check keeps the previous site and reports intact. Fix the source issue before retrying. GitHub's normal failed workflow notifications depend on your account notification settings.
4. The weekday 6:30 p.m. Eastern schedule and 7:20 p.m. retry both skip market holidays. The second run does not rewrite an already archived report. GitHub may delay scheduled runs, and may disable schedules in public repositories after 60 days without repository activity.
5. If the SEC requires a more specific contact, set repository **Settings → Secrets and variables → Actions → Variables** to an appropriate public project contact under `SEC_CONTACT`. Never enter a password there. The public job does not need market-data credentials.

## If EDGAR blocks the hosted runner

The initial locally verified report is archived in this repository. The hosted runner received HTTP 403 for both SEC identifier and submissions endpoints. GitHub marks these attempts failed and keeps the previous deployment. A dated SEC ticker snapshot can fill Nasdaq-100 identifiers if the ticker endpoint is unavailable. The collector still requires the live filing and financial-data endpoints.

If you have an existing computer that can reach EDGAR, a free local scheduler can run the collector after 6:30 p.m. Eastern and push its public archive. Use a dedicated, clean checkout on `main` with existing GitHub write authentication and the Python environment set up. Run the following from that checkout under a scheduler that prevents overlap. GitHub Pages publishes when the archive index changes.

```bash
set -e
git pull --ff-only origin main
.venv/bin/python monitor.py public
git add -- site/data/
if ! git diff --cached --quiet; then
  git commit -m 'Archive verified SEC research report'
fi
git push origin main
```

The computer must be online and awake. The scanner stops before publishing on source errors and skips market holidays. The public workflow and local collector should use the same dedicated archive rather than editing report JSON by hand.

## Private price scanner

1. Create a **Stocks Basic ($0)** account with [Massive](https://massive.com/pricing?product=stocks) and copy your API key from its dashboard. Use the key on your own computer. Keep it out of chat and GitHub.
2. Clone this repository. With Python 3.12 installed, run these commands in the project folder. The key prompt hides what you paste.

   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   .venv/bin/python -c 'import getpass, os, subprocess, sys; key = getpass.getpass("Massive API key: "); sys.exit(subprocess.call([sys.executable, "monitor.py", "private", "--provider", "massive", "--prices-only"], env={**os.environ, "MASSIVE_API_KEY": key}))'
   ```

3. The scan uses the most recent trading session available after midnight Eastern. It fetches split-adjusted daily summaries at the Basic plan's rate limit, so allow around an hour. The terminal prints up to ten matches and saves the full report under `.private/data/`.
4. Click **Open a scan file** on the dashboard and choose the dated report. The browser reads it locally. The report stays on your device and clears when you reload.

The first scan intentionally focuses on prices. To add company filings and financial facts, remove `--prices-only` and run again. Missing price bars stop the scan. The Massive adapter still needs live verification with an entitled key. [Basic plan timing](https://massive.com/knowledge-base/article/on-the-free-basic-plan-when-can-i-pull-the-previous-trading-days-data) · [Personal-use terms](https://massive.com/legal/market-data-terms-of-service)

An existing Alpaca account entitled to delayed consolidated SIP history is also supported. Provide `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, and `APCA_PERSONAL_USE=yes` in your local process environment and use `--provider alpaca --latest` in place of `--provider massive`. Alpaca documents IEX entitlement for paper-only accounts. Confirm SIP entitlement before choosing this option.

## Optional public SEC digest via Google Apps Script

Create a standalone project at [Google Apps Script](https://script.google.com/), paste `Email.gs`, and use **Project Settings → Script properties** to add `RECIPIENTS` with the two intended addresses separated by a comma. Keep those addresses in script properties. The script polls the project's fixed HTTPS dashboard and never exposes an inbound mail endpoint.

Use `sendDemoOnce` only if a demonstration email has not already been sent. The deployed script has a test claim after the one-off Gmail demo, which prevents an accidental duplicate. The account owner must grant URL fetching and MailApp send authorization if prompted. Then run `installSecDigest` if you want the public SEC-only digest. It checks after 6:30 p.m. ET on weekdays, requires an archive dated that same day, and records a send claim before calling MailApp. If delivery is ambiguous it does not retry automatically. Inspect Apps Script **Executions** before clearing the day's claim. A MailApp success indicates acceptance for sending. Verify inbox delivery separately. To stop the digest, remove its trigger from **Triggers**.

The current implementation does not email licensed prices. Enabling a full market report to two recipients requires terms that allow that audience and usage.

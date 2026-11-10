# Setup and troubleshooting

## Website and SEC archive

1. In repository **Settings → Pages**, use **GitHub Actions** as the source. The repository is already public.
2. In **Actions → Market Low Monitor → Run workflow**, select `main` and keep **Refresh SEC data** checked. During the trading day the manual run uses the latest completed session with the roster observed on the day of the run.
3. Expand **Refresh SEC archive** in the job log for the number of securities verified. The deploy job reports the live URL. A failed source check keeps the previous site and reports intact. Fix the source issue before retrying. GitHub's normal failed workflow notifications depend on your account notification settings.
4. The weekday 6:30 p.m. Eastern schedule and 7:20 p.m. retry both skip market holidays. The second run does not rewrite an already archived report. GitHub may delay scheduled runs, and may disable schedules in public repositories after 60 days without repository activity.
5. If the SEC requires a more specific contact, set repository **Settings → Secrets and variables → Actions → Variables** to an appropriate public project contact under `SEC_CONTACT`. Never enter a password there. The public job does not need market-data credentials.

## Private price scanner

1. Clone this repository. Install Python 3.12, create a virtual environment, and install `requirements.txt`.
2. If an existing Alpaca Basic paper/data account allows delayed SIP history for personal use, confirm the regular-session price convention, split adjustment and ticker coverage against known exchange closing prices before enabling live use. This provider path has no verified full live scan in this release.
3. Supply your own paper/data key and secret through the local process environment as `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY`. Set `APCA_PERSONAL_USE=yes` after completing step 2. Do not add credentials or reports to GitHub. No trade endpoint is called.
4. Run `python monitor.py private` after the market closes and the delayed feed is ready, or `python monitor.py private --latest` to select the most recent closed session. Run it with your operating system's scheduler at 6:30 p.m. Eastern for local automation. A scheduled local run requires the computer to be awake and online.
5. Open **Private reports** on the dashboard and select one or more date-named JSON files from `.private/data/`. The site parses them in memory. The files and market-derived results stay on your device. Keep your browser watchlist on the browser profile where you use it.

Missing regular-session bars abort the scan. Do not change from delayed SIP to IEX silently because they represent different market coverage. Confirm symbol mappings if the provider rejects share classes.

## Optional public SEC digest via Google Apps Script

Create a standalone project at [Google Apps Script](https://script.google.com/), paste `Email.gs`, and use **Project Settings → Script properties** to add `RECIPIENTS` with the two intended addresses separated by a comma. Keep those addresses in script properties. The script polls the project's fixed HTTPS dashboard and never exposes an inbound mail endpoint.

Run `sendDemoOnce` once to deliver a visibly fictional report to both recipients. The account owner must grant URL fetching and MailApp send authorization if prompted. Then run `installSecDigest` if you want the public SEC-only digest. It checks after 6:30 p.m. ET on weekdays, requires an archive dated that same day, and records a send claim before calling MailApp. If delivery is ambiguous it does not retry automatically. Inspect Apps Script **Executions** before clearing the day's claim. A MailApp success indicates acceptance for sending. Verify inbox delivery separately. To stop the digest, remove its trigger from **Triggers**.

The current implementation does not email licensed prices. Enabling a full market report to two recipients requires terms that allow that audience and usage.

const SITE = "https://louiscmancuso.github.io/market-low-monitor/";
const ET = "America/New_York";

function recipients_() {
  const list = (PropertiesService.getScriptProperties().getProperty("RECIPIENTS") || "")
    .split(",").map(value => value.trim()).filter(Boolean);
  if (list.length !== 2 || new Set(list.map(value => value.toLowerCase())).size !== 2 ||
      list.some(value => !/^[^\s,;<>@]+@[^\s,;<>@]+\.[^\s,;<>@]+$/.test(value))) {
    throw new Error("Set RECIPIENTS to exactly two distinct addresses in Script properties.");
  }
  return list;
}

function html_(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}

function get_(path) {
  const response = UrlFetchApp.fetch(SITE + path, {followRedirects: false, muteHttpExceptions: true});
  if (response.getResponseCode() !== 200) throw new Error("Public dashboard data unavailable.");
  return JSON.parse(response.getContentText());
}

function installSecDigest() {
  recipients_();
  for (const trigger of ScriptApp.getProjectTriggers()) {
    if (trigger.getHandlerFunction() === "sendSecDigest") ScriptApp.deleteTrigger(trigger);
  }
  ScriptApp.newTrigger("sendSecDigest").timeBased().everyMinutes(15).create();
}

function sendSecDigest() {
  const now = new Date();
  const day = Utilities.formatDate(now, ET, "yyyy-MM-dd");
  const clock = Utilities.formatDate(now, ET, "HHmm");
  if (["Sat", "Sun"].includes(Utilities.formatDate(now, ET, "EEE")) || clock < "1830") return;
  const properties = PropertiesService.getScriptProperties();
  if (properties.getProperty("LAST_SEC_DIGEST") >= day) return;
  const dates = get_("data/index.json");
  if (!Array.isArray(dates) || dates[0] !== day) return;
  const report = get_("data/" + day + ".json");
  if (report.mode !== "public" || report.date !== day || !Array.isArray(report.rows) ||
      report.rows.length < 495) throw new Error("Unexpected SEC report contents.");
  const filed = report.rows.filter(row => row.filings.length);
  const latest = filed.slice().sort((a, b) => b.filings[0].filed.localeCompare(a.filings[0].filed) ||
    a.ticker.localeCompare(b.ticker)).slice(0, 5);
  const rows = latest.map(row => [row.ticker, row.name, row.filings[0].form, row.filings[0].filed,
    (row.observations || []).slice(0, 2).join(" ") || "See the source filing."]);
  const body = "<p>SEC-only update. This report does not contain verified market prices or a 52-week-low scan.</p>" +
    "<h2>Daily summary</h2><p>" + report.rows.length + " monitored securities and " + filed.length +
    " with recent filings.</p><h2>Filings to review</h2>" +
    table_(["Ticker", "Company", "Form", "Filed", "Financial observations"], rows) +
    "<h2>Changes since the previous session</h2><p>" +
    (report.comparable ? html_(report.researchChanges.join(", ") || "No newly tracked filings.") :
      "No immediately preceding report for comparison.") + "</p>";
  sendOnce_("LAST_SEC_DIGEST", day, "Market Low Monitor | " + day + " | SEC Research Digest", body);
}

function sendDemoOnce() {
  if (UrlFetchApp.fetch(SITE, {muteHttpExceptions: true}).getResponseCode() !== 200) {
    throw new Error("The dashboard must be live before sending a demo.");
  }
  const body = "<p><strong>Demonstration only. The companies, prices and developments below are fictional.</strong></p>" +
    "<h2>Daily executive summary</h2><p>7 fictional securities screened, 6 qualify, 1 newly qualifies and 1 makes a fresh low.</p>" +
    "<h2>Five example research leads</h2>" +
    table_(["Ticker", "Priority", "Example follow-up"], [
      ["EXM-A", "High", "Compare revenue and margins"], ["EXM-G", "High", "Review cash flow"],
      ["EXM-D", "Medium", "Check debt maturities"], ["EXM-C", "Medium", "Review annual earnings"],
      ["EXM-B", "Low", "Check funding needs"]
    ]) + "<h2>Full fictional qualifying list</h2>" +
    table_(["Ticker", "Close", "Low", "Above low", "Above low %"], [
      ["EXM-E", "$31.80", "$31.80", "$0.00", "0.00%"], ["EXM-A", "$42.18", "$40.00", "$2.18", "5.45%"],
      ["EXM-D", "$68.00", "$62.00", "$6.00", "9.68%"], ["EXM-C", "$275.25", "$250.75", "$24.50", "9.77%"],
      ["EXM-G", "$65.00", "$55.00", "$10.00", "18.18%"], ["EXM-B", "$16.20", "$10.00", "$6.20", "62.00%"]
    ]) + "<h2>Changes since the previous example</h2><p>New EXM-D. Fresh low EXM-E. Exited EXM-F.</p>";
  sendOnce_("DEMO_SENT", "once", "Market Low Monitor | 2024-05-14 | 6 Stocks Near 52-Week Lows [DEMO]", body);
}

function table_(headings, rows) {
  const headingsHtml = headings.map(heading => '<th style="padding:7px;text-align:left;background:#e8f0fb">' +
    html_(heading) + "</th>").join("");
  const rowsHtml = rows.map(row => "<tr>" + row.map(value =>
    '<td style="padding:7px;border-bottom:1px solid #dbe3ed">' + html_(value) + "</td>").join("") + "</tr>").join("");
  return '<table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr>' +
    headingsHtml + "</tr></thead><tbody>" + rowsHtml + "</tbody></table>";
}

function sendOnce_(key, claim, subject, reportBody) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) return;
  try {
    const properties = PropertiesService.getScriptProperties();
    const previous = properties.getProperty(key);
    if (previous && previous >= claim) return;
    const recipients = recipients_();
    if (MailApp.getRemainingDailyQuota() < recipients.length) throw new Error("Insufficient MailApp quota.");
    const body = '<div style="font:15px Calibri,Arial,sans-serif;max-width:700px;color:#162b45;margin:auto">' +
      "<h1>Market Low Monitor</h1>" + reportBody + '<h2>Full dashboard</h2><p><a href="' + SITE +
      '">Open Market Low Monitor</a></p></div>';
    properties.setProperty(key, claim);
    MailApp.sendEmail({to: recipients.join(","), subject,
      body: subject + "\n" + (key === "DEMO_SENT" ? "Fictional test data. " : "SEC filing activity only. ") + SITE,
      htmlBody: body, name: "Market Low Monitor"});
    console.log("MailApp accepted a single report for sending.");
  } finally {
    lock.releaseLock();
  }
}

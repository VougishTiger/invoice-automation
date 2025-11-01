import os
import io
import pdfkit
import smtplib
from email.message import EmailMessage
from flask import Flask, request, render_template_string, send_file
from datetime import date
import shutil

EMAIL_USER= os.getenv("EMAIL_USER", "")
EMAIL_PASS= os.getenv("EMAIL_PASS","")

TPL= """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{{ invoice_id }} - Receipt</title>
<style>
:root{
  --bg:#0f172a;
  --panel:#1e293b;
  --border:#334155;
  --text:#f1f5f9;
  --muted:#94a3b8;
  --accent:#38bdf8;
  --glow:0 0 15px rgba(56,189,248,0.4);
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);color:var(--text);font-family:"Inter",Arial,Helvetica,sans-serif;line-height:1.5}
.paper{
  width:820px;
  margin:40px auto;
  background:rgba(30,41,59,0.9);
  border:1px solid var(--border);
  border-radius:16px;
  padding:50px;
  box-shadow:0 8px 30px rgba(0,0,0,0.5);
  backdrop-filter:blur(10px);
}
.header{
  display:flex;
  justify-content:space-between;
  align-items:flex-start;
  padding-bottom:24px;
  border-bottom:2px solid var(--border);
  gap:18px;
}
.brandwrap{display:flex;gap:14px;align-items:flex-start}
.logoimg{
  width:56px;height:56px;border-radius:10px;border:1px solid var(--border);
  object-fit:cover; background:#0b1220
}
h1{
  font-size:32px;
  letter-spacing:1px;
  text-transform:uppercase;
  color:var(--accent);
  text-shadow:var(--glow);
  margin-bottom:6px
}
.brand{font-weight:700;font-size:18px;color:var(--text);margin-top:4px}
.muted{color:var(--muted);font-size:14px}
.meta{text-align:right;font-size:14px;color:var(--muted)}
.meta b{color:var(--text)}
h3{margin:28px 0 10px 0;font-size:18px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.billto{
  background:rgba(15,23,42,0.8);
  border:1px solid var(--border);
  border-radius:12px;
  padding:16px 18px;
  box-shadow:inset 0 0 10px rgba(56,189,248,0.2);
}
.billto strong{font-size:16px;color:var(--text)}
.billto .muted{font-size:13px}
table{
  width:100%;
  border-collapse:collapse;
  margin-top:24px;
}
th,td{
  padding:12px 14px;
  border-bottom:1px solid var(--border);
  font-size:15px;
}
th{
  text-align:left;
  color:var(--accent);
  text-transform:uppercase;
  letter-spacing:.5px;
  font-weight:600;
}
.right{text-align:right}
.totals{
  width:360px;
  margin-left:auto;
  margin-top:28px;
  background:rgba(15,23,42,0.8);
  border:1px solid var(--border);
  border-radius:12px;
  box-shadow:var(--glow);
  overflow:hidden;
}
.totals table{margin:0}
.totals td,.totals th{
  border:none;
  padding:12px 14px;
  font-size:16px;
}
.totals th{text-align:right;color:var(--accent)}
.note{
  margin-top:30px;
  font-size:14px;
  color:var(--muted);
  padding:14px;
  background:rgba(30,41,59,0.6);
  border-left:3px solid var(--accent);
  border-radius:8px;
}
.footer{
  text-align:center;
  margin-top:40px;
  font-size:13px;
  color:var(--muted);
  letter-spacing:.5px;
}
@page{size:Letter;margin:12mm}
</style>
</head>
<body>
<div class="paper">
  <div class="header">
    <div class="brandwrap">
      {% if logo %}<img class="logoimg" src="{{ logo }}" alt="logo">{% endif %}
      <div>
        <h1>RECEIPT</h1>
        <div class="brand">{{ business_name }}</div>
        <div class="muted">{{ business_address }}</div>
        <div class="muted">{{ business_email }}</div>
      </div>
    </div>
    <div class="meta">
      <div><b>Receipt #:</b> {{ invoice_id }}</div>
      <div><b>Date:</b> {{ invoice_date }}</div>
      <div><b>Due:</b> {{ due_date }}</div>
    </div>
  </div>
  <h3>Billed To</h3>
  <div class="billto">
    <div><strong>{{ client_name }}</strong></div>
    <div class="muted">{{ client_address }}</div>
    <div class="muted">{{ client_email }}</div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Description</th>
        <th class="right">Qty</th>
        <th class="right">Unit Price</th>
        <th class="right">Line Total</th>
      </tr>
    </thead>
    <tbody>
      {{ rows }}
    </tbody>
  </table>

  <div class="totals">
    <table>
      <tr><td>Subtotal</td><td class="right">{{ subtotal }}</td></tr>
      <tr><td>Tax</td><td class="right">{{ tax }}</td></tr>
      <tr><th>Total</th><th class="right">{{ total }}</th></tr>
    </table>
  </div>

  <div class="note"><strong>Notes:</strong> {{ notes }}</div>
  <div class="footer">Thank you for your business.</div>
</div>
</body>
</html>"""

FORM= """<!doctype html>
<html>
<head>
<meta charset="utf-8"><title>Create Receipt</title>
<style>
:root{
  --bg0:#0b1220; --bg1:#0f172a; --card:#0b1220cc; --muted:#9aa4b2; --text:#e5e7eb;
  --line:#223047; --accent:#60a5fa; --accent2:#22d3ee; --btnText:#071225; --ring:0 0 0 3px rgba(96,165,250,.25)
}
:root[data-theme="light"]{
  --bg0:#eef2ff; --bg1:#f8fafc; --card:#ffffffcc; --muted:#475569; --text:#0f172a;
  --line:#dbe2f0; --accent:#2563eb; --accent2:#06b6d4; --btnText:#ffffff; --ring:0 0 0 3px rgba(37,99,235,.22)
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{
  font-family:"Inter",system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
  color:var(--text);
  background:
    radial-gradient(1200px 800px at 10% 10%, var(--accent2)20 0%, transparent 60%),
    radial-gradient(1200px 800px at 90% 30%, var(--accent)20 0%, transparent 60%),
    linear-gradient(180deg, var(--bg0) 0%, var(--bg1) 100%);
  min-height:100vh; display:flex;align-items:center;justify-content:center; padding:28px;
}
.wrapper{ width:100%; max-width:980px; position:relative }
.header{ display:flex; align-items:center; justify-content:space-between; margin:0 auto 14px auto; max-width:980px }
.brand{ display:flex;gap:10px;align-items:center; letter-spacing:.4px; font-weight:700 }
.brand .dot{ width:10px;height:10px;border-radius:50%; background:conic-gradient(from 0deg,var(--accent),var(--accent2),var(--accent)); box-shadow:0 0 20px var(--accent2) }
.header small{ color:var(--muted) }

.theme-toggle{ display:flex; align-items:center; gap:10px }
.switch{ position:relative; width:48px; height:26px }
.switch input{ opacity:0; width:0; height:0 }
.slider{
  position:absolute; cursor:pointer; inset:0; background:#1b2740; border:1px solid var(--line); border-radius:999px;
  transition:.2s; box-shadow: inset 0 1px 0 rgba(255,255,255,.04)
}
.slider:before{
  content:""; position:absolute; height:20px; width:20px; left:3px; top:2px; background:#e2e8f0; border-radius:50%;
  transition:.2s; box-shadow:0 2px 6px rgba(0,0,0,.25)
}
.switch input:checked + .slider{ background:#2b8fff }
.switch input:checked + .slider:before{ transform:translateX(22px); background:#fff }

.card{
  background:var(--card); backdrop-filter: blur(12px) saturate(120%);
  border:1px solid var(--line); border-radius:16px;
  box-shadow: 0 20px 40px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.02);
  overflow:hidden;
}
.card .topbar{
  display:flex;align-items:center;justify-content:space-between;
  padding:14px 18px; background:linear-gradient( to right, color-mix(in oklab, var(--bg0) 85%, black), color-mix(in oklab, var(--bg0) 75%, black) );
  border-bottom:1px solid var(--line);
}
.topbar h2{font-size:18px;font-weight:700;letter-spacing:.3px}
.grid{ display:grid; gap:16px; grid-template-columns: repeat(12, 1fr); padding:18px }
.section{
  border:1px solid var(--line); border-radius:12px; padding:16px;
  background: linear-gradient(180deg, color-mix(in oklab, var(--bg1) 88%, black), color-mix(in oklab, var(--bg1) 78%, black));
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.02);
}
.section h3{ font-size:13px; text-transform:uppercase; letter-spacing:.14em; color:var(--muted); margin-bottom:10px }
.col-6{grid-column: span 6}.col-12{grid-column: span 12}

label{ display:block; font-size:13px; color:var(--muted); margin-bottom:6px }
input,textarea{
  width:100%; color:var(--text); background:color-mix(in oklab, var(--bg0) 10%, black);
  border:1px solid var(--line); border-radius:10px; padding:10px 12px; font-size:14px;
  transition:border-color .2s, box-shadow .2s, transform .08s;
}
textarea{min-height:84px;resize:vertical}
input::placeholder,textarea::placeholder{ color:color-mix(in oklab, var(--muted) 70%, black) }
input:focus,textarea:focus{ outline:none; border-color:var(--accent); box-shadow:var(--ring) }
input:active{ transform:scale(.998) }

[data-theme="light"] input,[data-theme="light"] textarea{
  background:#ffffff;
  color:#0f172a;
  border:1px solid var(--line);
}

.tablewrap{ border:1px dashed var(--line); border-radius:10px; padding:10px; background:color-mix(in oklab, var(--bg1) 65%, black) }
table{ width:100%; border-collapse:collapse }
th,td{ padding:10px 10px; border-bottom:1px solid var(--line); font-size:14px }
th{ color:color-mix(in oklab, var(--accent) 80%, white); text-align:left; font-weight:600 }
td input{ background:color-mix(in oklab, var(--bg0) 12%, black) }

[data-theme="light"] td input{
  background:#ffffff;
  color:#0f172a;
  border:1px solid var(--line);
}

.logo-box{ display:flex; align-items:center; gap:12px; margin-top:6px }
.logo-preview{
  width:56px; height:56px; border-radius:10px; border:1px solid var(--line);
  background:color-mix(in oklab, var(--bg1) 75%, black) center/cover no-repeat;
}

.actions{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; justify-content:flex-end; padding:16px; border-top:1px solid var(--line); background:color-mix(in oklab, var(--bg0) 85%, black) }
.btn{
  appearance:none; border:none; cursor:pointer; padding:10px 14px; border-radius:10px; font-weight:600;
  letter-spacing:.3px; transition:transform .08s ease, box-shadow .2s ease, opacity .2s ease;
}
.btn:active{ transform:translateY(1px) }
.btn-primary{
  background:linear-gradient(135deg,var(--accent),var(--accent2)); color:var(--btnText);
  box-shadow:0 10px 25px color-mix(in oklab, var(--accent) 35%, transparent), 0 0 0 1px color-mix(in oklab, var(--accent) 50%, black) inset;
}
.btn-primary:hover{ box-shadow:0 12px 28px color-mix(in oklab, var(--accent) 50%, transparent), 0 0 0 1px color-mix(in oklab, var(--accent) 65%, black) inset }
.btn-ghost{ background:transparent; color:var(--muted); border:1px solid var(--line) }
.kbd{
  font-family:ui-monospace,Menlo,Consolas,monospace; display:inline-block; padding:2px 6px;
  border-radius:6px; border:1px solid var(--line); background:color-mix(in oklab, var(--bg0) 88%, black); color:var(--muted); font-size:12px
}

.loading{
  position:fixed; inset:0; display:none; place-items:center; backdrop-filter:blur(6px);
  background:rgba(0,0,0,.35); z-index:50
}
.loading.show{ display:grid }
.spinner{
  width:72px;height:72px;border-radius:50%;
  background:
    conic-gradient(from 0deg, var(--accent), var(--accent2), var(--accent)) border-box;
  -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 12px), #000 0);
  mask: radial-gradient(farthest-side, transparent calc(100% - 12px), #000 0);
  animation: spin 1s linear infinite;
  box-shadow: 0 0 40px color-mix(in oklab, var(--accent) 40%, transparent);
}
@keyframes spin{ to{ transform: rotate(360deg) } }
.shimmer{
  margin-top:12px; height:10px; width:220px; border-radius:999px;
  background:linear-gradient(90deg, #ffffff22, #ffffff55, #ffffff22);
  background-size:200% 100%; animation: shimmer 1.3s infinite linear
}
@keyframes shimmer{ to{ background-position: -200% 0 } }

@media (max-width:920px){ .grid{grid-template-columns:1fr} .col-6,.col-12{grid-column:auto} }
</style>
<script>
function addRow(){
  const t=document.getElementById('items');const r=t.insertRow(-1);
  r.innerHTML='<td><input name="description" placeholder="Description" required></td><td><input name="qty" type="number" step="0.01" placeholder="Qty" required></td><td><input name="unit_price" type="number" step="0.01" placeholder="Unit Price" required></td>';
}
function setTheme(t){ document.documentElement.setAttribute('data-theme', t); localStorage.setItem('sr_theme', t); }
function initTheme(){
  const saved=localStorage.getItem('sr_theme'); const prefers=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';
  const theme=saved||prefers; setTheme(theme);
  const chk=document.getElementById('themeChk'); if(chk) chk.checked=(theme==='light');
}
function onThemeToggle(e){ setTheme(e.target.checked?'light':'dark'); }
function onLogoChange(e){
  const f=e.target.files && e.target.files[0]; if(!f) return;
  if(!f.type.startsWith('image/')) return alert('Please select an image file.');
  const r=new FileReader(); r.onload=ev=>{ document.querySelector('.logo-preview').style.backgroundImage='url('+ev.target.result+')'; document.getElementById('logo_data').value=ev.target.result; };
  r.readAsDataURL(f);
}
function onSubmitStart(){ document.querySelector('.loading').classList.add('show'); }
document.addEventListener('DOMContentLoaded', ()=>{
  initTheme();
  const chk=document.getElementById('themeChk'); if(chk) chk.addEventListener('change', onThemeToggle);
  const logo=document.getElementById('logo_file'); if(logo) logo.addEventListener('change', onLogoChange);
  const form=document.querySelector('form'); form.addEventListener('submit', onSubmitStart);
  document.querySelector('input[name=invoice_date]').value=new Date().toISOString().slice(0,10);
  addRow();
});
</script>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <div class="brand"><span class="dot"></span> InstaVoicePDF <small class="kbd">v1</small></div>
    <div class="theme-toggle">
      <small>Light</small>
      <label class="switch">
        <input id="themeChk" type="checkbox"><span class="slider"></span>
      </label>
      <small>Dark</small>
    </div>
  </div>

  <div class="card">
    <div class="topbar">
      <h2>Create & Email Receipt</h2>
      <div><span class="kbd">Tab</span> to move · <span class="kbd">Enter</span> to submit</div>
    </div>

    <form method="post" action="/submit" enctype="multipart/form-data">
      <input type="hidden" name="logo_data" id="logo_data">
      <div class="grid">
        <div class="section col-6">
          <h3>Business</h3>
          <label>Business Name</label>
          <input name="business_name" placeholder="Your LLC, Inc., etc." required>
          <label>Business Address</label>
          <input name="business_address" placeholder="123 Main St, City, ST ZIP" required>
          <label>Business Email</label>
          <input name="business_email" placeholder="you@company.com" required>
          <label>Logo (optional)</label>
          <div class="logo-box">
            <div class="logo-preview"></div>
            <input id="logo_file" type="file" accept="image/*">
          </div>
        </div>

        <div class="section col-6">
          <h3>Receipt</h3>
          <label>Receipt / Invoice ID</label>
          <input name="invoice_id" placeholder="INV-1001" required>
          <label>Invoice Date</label>
          <input name="invoice_date" placeholder="YYYY-MM-DD" required>
          <label>Due Date</label>
          <input name="due_date" placeholder="YYYY-MM-DD" required>
          <label>Notes</label>
          <textarea name="notes" placeholder="Optional message or payment terms"></textarea>
        </div>

        <div class="section col-6">
          <h3>Client</h3>
          <label>Client Name</label>
          <input name="client_name" placeholder="Client full name" required>
          <label>Client Email</label>
          <input name="client_email" placeholder="client@email.com" required>
          <label>Client Address</label>
          <input name="client_address" placeholder="Address or company details" required>
        </div>

        <div class="section col-6">
          <h3>Tax & Delivery</h3>
          <label>Tax Rate</label>
          <input name="tax_rate" type="number" step="0.0001" value="0.0825" required>
          <label>Send Copy To (Owner Email)</label>
          <input name="owner_email" placeholder="owner@company.com" required>
        </div>

        <div class="section col-12">
          <h3>Items</h3>
          <div class="tablewrap">
            <table>
              <thead><tr><th>Description</th><th>Qty</th><th>Unit Price</th></tr></thead>
              <tbody id="items"></tbody>
            </table>
          </div>
          <div class="actions" style="justify-content:flex-start;padding-left:0;margin-top:10px;border-top:none">
            <button type="button" class="btn btn-ghost" onclick="addRow()">+ Add Item</button>
          </div>
        </div>
      </div>

      <div class="actions">
        <button type="button" class="btn btn-ghost" onclick="addRow()">+ Add Item</button>
        <button type="submit" class="btn btn-primary">Generate & Send</button>
      </div>
    </form>
  </div>
</div>

<div class="loading" aria-hidden="true">
  <div>
    <div class="spinner"></div>
    <div class="shimmer"></div>
  </div>
</div>
</body>
</html>"""

app= Flask(__name__)

def money(x): return f"${x:,.2f}"

def send_mail(to_email, subject, body, pdf_bytes, fname):
  msg=EmailMessage()
  msg["From"]= EMAIL_USER
  msg["To"]= to_email
  msg["Subject"]= subject
  msg.set_content(body)
  msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename= fname)
  with smtplib.SMTP_SSL("smtp.gmail.com",465) as s:
    s.login(EMAIL_USER, EMAIL_PASS)
    s.send_message(msg)


@app.get("/")
def index():
  return render_template_string(FORM)

@app.post("/submit")
def submit():
  inv= {
    "business_name": request.form.get("business_name",""),
    "business_address": request.form.get("business_address",""),
    "business_email": request.form.get("business_email",""),
    "invoice_id": request.form.get("invoice_id",""),
    "invoice_date": request.form.get("invoice_date",""),
    "due_date": request.form.get("due_date",""),
    "notes": request.form.get("notes",""),
    "client_name": request.form.get("client_name",""),
    "client_email": request.form.get("client_email",""),
    "client_address": request.form.get("client_address",""),
    "logo": request.form.get("logo_data","")
  }
  tax_rate= float(request.form.get("tax_rate","0") or 0)
  descs= request.form.getlist("description")
  qtys= request.form.getlist("qty")
  prices= request.form.getlist("unit_price")
  rows_html= []
  subtotal= 0.0
  for d,q,p in zip(descs,qtys,prices):
    if not (d and q and p): continue
    qv= float(q); pv= float(p); lt= qv*pv; subtotal+= lt
    rows_html.append(f"<tr><td>{d}</td><td class='right'>{qv:.2f}</td><td class='right'>{money(pv)}</td><td class='right'>{money(lt)}</td></tr>")
  tax= round(subtotal*tax_rate,2)
  total= subtotal+tax
  ctx= {**inv,"rows":"\n".join(rows_html) if rows_html else "<tr><td colspan='4'>No items</td></tr>","subtotal": money(subtotal),"tax": money(tax),"total": money(total)}
  candidates= [
    os.path.join(os.getcwd(),"bin","wkhtmltopdf"),
    "/opt/render/project/src/bin/wkhtmltopdf",
    "/usr/local/bin/wkhtmltopdf",
    "/usr/bin/wkhtmltopdf"
  ]
  wkhtml= next((p for p in candidates if os.path.exists(p)), None) or shutil.which("wkhtmltopdf")
  if not wkhtml:
    return "wkhtmltopdf not found on this system. Install it or add it to PATH.", 500
  config= pdfkit.configuration(wkhtmltopdf= wkhtml)
  try:
    pdf_bytes= pdfkit.from_string(render_template_string(TPL, **ctx), False, configuration= config, options={"page-size":"Letter","margin-top":"10mm","margin-right":"10mm","margin-bottom":"10mm","margin-left":"10mm","quiet":"","no-print-media-type":None,"disable-smart-shrinking":""})
  except Exception as e:
    return str(e), 500
  fname= f"{inv['invoice_id']}.pdf"
  try:
    if EMAIL_USER and EMAIL_PASS and inv["client_email"]:
      send_mail(inv["client_email"], f"Receipt {inv['invoice_id']}", f"Your receipt total {ctx['total']}.", pdf_bytes, fname)
    owner_email= request.form.get("owner_email","")
    if EMAIL_USER and EMAIL_PASS and owner_email:
      send_mail(owner_email, f"Receipt {inv['invoice_id']}", f"Copy of receipt {inv['invoice_id']} total {ctx['total']}.", pdf_bytes, fname)
  except Exception:
    pass
  return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True, download_name=fname)

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=int(os.getenv("PORT","5000")), debug=True)
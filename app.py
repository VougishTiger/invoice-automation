import os
import io
import pdfkit
import smtplib
from email.message import EmailMessage
from flask import Flask, request, render_template_string, send_file
from datetime import date

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
}
h1{
  font-size:32px;
  letter-spacing:1px;
  text-transform:uppercase;
  color:var(--accent);
  text-shadow:var(--glow);
}
.brand{font-weight:700;font-size:18px;color:var(--text);margin-top:8px}
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
    <div>
      <h1>RECEIPT</h1>
      <div class="brand">{{ business_name }}</div>
      <div class="muted">{{ business_address }}</div>
      <div class="muted">{{ business_email }}</div>
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
body{
  margin:0;
  font-family:"Inter",Arial,Helvetica,sans-serif;
  background:linear-gradient(135deg,#2563eb,#0ea5e9);
  color:#111;
  min-height:100vh;
  display:flex;
  align-items:center;
  justify-content:center;
}
.container{
  width:95%;
  max-width:900px;
  background:rgba(255,255,255,0.95);
  backdrop-filter:blur(10px);
  border-radius:16px;
  box-shadow:0 10px 30px rgba(0,0,0,0.2);
  padding:40px 50px;
}
h2{
  text-align:center;
  margin-bottom:20px;
  color:#1e3a8a;
  font-size:28px;
  letter-spacing:.5px;
}
h3{
  margin-top:28px;
  color:#1e40af;
  border-left:4px solid #3b82f6;
  padding-left:10px;
  font-size:18px;
}
input,textarea{
  width:100%;
  padding:10px 12px;
  margin:6px 0 14px 0;
  border:1px solid #d1d5db;
  border-radius:8px;
  font-size:15px;
  transition:all .2s ease;
}
input:focus,textarea:focus{
  border-color:#3b82f6;
  outline:none;
  box-shadow:0 0 0 3px rgba(59,130,246,0.2);
}
table{
  width:100%;
  border-collapse:collapse;
  margin-top:10px;
  background:#f9fafb;
  border-radius:8px;
  overflow:hidden;
}
th,td{
  border:1px solid #e5e7eb;
  padding:10px;
  font-size:14px;
}
th{
  background:#eff6ff;
  text-align:left;
  color:#1e40af;
  font-weight:600;
}
button{
  background:#3b82f6;
  color:#fff;
  border:none;
  border-radius:8px;
  padding:12px 18px;
  font-size:15px;
  cursor:pointer;
  margin-top:10px;
  transition:background .2s ease,transform .1s ease;
}
button:hover{background:#2563eb;transform:translateY(-2px);}
button:active{transform:translateY(0);}
footer{
  text-align:center;
  color:#64748b;
  font-size:13px;
  margin-top:20px;
}
</style>
<script>
function addRow(){const t=document.getElementById('items');const r=t.insertRow(-1);r.innerHTML='<td><input name="description" placeholder="Description" required></td><td><input name="qty" type="number" step="0.01" placeholder="Qty" required></td><td><input name="unit_price" type="number" step="0.01" placeholder="Unit Price" required></td>'; }
</script>
</head>
<body>
<div class="container">
<h2>Create and Email Receipt</h2>
<form method="post" action="/submit">
  <h3>Business</h3>
  <input name="business_name" placeholder="Business Name" required>
  <input name="business_address" placeholder="Business Address" required>
  <input name="business_email" placeholder="Business Email" required>
  <h3>Receipt</h3>
  <input name="invoice_id" placeholder="Receipt/Invoice ID" required>
  <input name="invoice_date" placeholder="YYYY-MM-DD" required>
  <input name="due_date" placeholder="YYYY-MM-DD" required>
  <textarea name="notes" placeholder="Notes"></textarea>
  <h3>Client</h3>
  <input name="client_name" placeholder="Client Name" required>
  <input name="client_email" placeholder="Client Email" required>
  <input name="client_address" placeholder="Client Address" required>
  <h3>Items</h3>
  <table><thead><tr><th>Description</th><th>Qty</th><th>Unit Price</th></tr></thead><tbody id="items"></tbody></table>
  <button type="button" onclick="addRow()">+ Add Item</button>
  <h3>Tax Rate</h3>
  <input name="tax_rate" type="number" step="0.0001" value="0.0825" required>
  <h3>Email Copies To</h3>
  <input name="owner_email" placeholder="Business Owner Email" required>
  <button type="submit">Generate & Send</button>
</form>
<footer>© 2025 SmartReceipt – Powered by Flask</footer>
</div>
<script>document.querySelector('input[name=invoice_date]').value=new Date().toISOString().slice(0,10);addRow();</script>
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
  html= render_template_string(TPL, **ctx)
  pdf_bytes= pdfkit.from_string(html, False, options={"page-size":"Letter","margin-top":"10mm","margin-right":"10mm","margin-bottom":"10mm","margin-left":"10mm","quiet":"","no-print-media-type":None,"disable-smart-shrinking":""})
  fname= f"{inv['invoice_id']}.pdf"
  if EMAIL_USER and EMAIL_PASS and inv["client_email"]:
    send_mail(inv["client_email"], f"Receipt {inv['invoice_id']}", f"Your receipt total {ctx['total']}.", pdf_bytes, fname)
  owner_email= request.form.get("owner_email","")
  if EMAIL_USER and EMAIL_PASS and owner_email:
    send_mail(owner_email, f"Receipt {inv['invoice_id']}", f"Copy of receipt {inv['invoice_id']} total {ctx['total']}.", pdf_bytes, fname)
  return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True, download_name=fname)

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=int(os.getenv("PORT","5000")), debug=True)

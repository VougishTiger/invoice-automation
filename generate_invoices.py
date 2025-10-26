import csv
import os
import shutil
import pdfkit
import smtplib
from email.message import EmailMessage
import mimetypes
import re

BASE_DIR= os.path.dirname(os.path.abspath(__file__))
DATA_DIR= os.path.join(BASE_DIR, "data")
TPL_PATH= os.path.join(BASE_DIR, "templates", "invoice.html")
OUT_DIR= os.path.join(BASE_DIR, "out")

BUSINESS= {
  "business_name": "Your Business LLC",
  "business_address": "100 Example Rd, Los Banos, CA 93635",
  "business_email": "you@yourbusiness.com",
  "tax_rate": 0.0825,
}

EMAIL_USER= os.getenv("EMAIL_USER","")
EMAIL_PASS= os.getenv("EMAIL_PASS","")
SEND_EMAILS= True

def read_csv(filename):
  path= os.path.join(DATA_DIR, filename)
  with open(path, newline= "", encoding="utf-8") as f:
    return list(csv.DictReader(f))

def money(x):
  return f"${x:,.2f}"

def load_template():
  with open(TPL_PATH, "r", encoding="utf-8") as f:
    return f.read()

def render_template(template_str, context):
  html= template_str
  for k, v in context.items():
    html= html.replace(f"{{{{ {k} }}}}", str(v))
  return html

def find_wkhtmltopdf():
  candidates= [
    r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
    r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
    "/usr/local/bin/wkhtmltopdf",
    "/opt/homebrew/bin/wkhtmltopdf",
    "/usr/bin/wkhtmltopdf",
  ]
  for p in candidates:
    if os.path.exists(p):
      return p
  p= shutil.which("wkhtmltopdf")
  return p

def safe_filename(s):
  s= re.sub(r"[^\w\s\-.]", "", s, flags=re.UNICODE)
  s= re.sub(r"\s+", " ", s).strip().replace(" ","_")
  return s or "file"

def send_pdf(to_email, subject, body, pdf_path, from_email, from_pass):
  if not from_email or not from_pass:
    return False
  msg= EmailMessage()
  msg["From"]= from_email
  msg["To"]= to_email
  msg["Subject"]= subject
  msg.set_content(body)
  ctype, encoding= mimetypes.guess_type(pdf_path)
  if ctype is None:
    ctype= "application/octet-stream"
  maintype, subtype= ctype.split("/",1)
  with open(pdf_path,"rb") as f:
    msg.add_attachment(f.read(), maintype= maintype, subtype= subtype, filename= os.path.basename(pdf_path))
  with smtplib.SMTP_SSL("smtp.gmail.com",465) as s:
    s.login(from_email, from_pass)
    s.send_message(msg)
  return True

clients= read_csv("clients.csv")
invoices= read_csv("invoices.csv")
items= read_csv("items.csv")

clients_by_id= {c["client_id"]: c for c in clients}

items_by_invoice= {}
for it in items:
  inv_id= it["invoice_id"]
  items_by_invoice.setdefault(inv_id,[]).append(it)

os.makedirs(OUT_DIR, exist_ok= True)
template= load_template()

wkhtml= find_wkhtmltopdf()
pdf_config= pdfkit.configuration(wkhtmltopdf= wkhtml) if wkhtml else None
pdf_options= {
  "page-size": "Letter",
  "margin-top": "10mm",
  "margin-right": "10mm",
  "margin-bottom": "10mm",
  "margin-left": "10mm",
  "quiet": ""
}

for inv in invoices:
  invoice_id= inv["invoice_id"]
  client_id= inv["client_id"]

  client= clients_by_id.get(client_id, {
    "name": "UNKNOWN CLIENT",
    "email": "",
    "address": "" 
  })

  inv_items= items_by_invoice.get(invoice_id, [])

  rows_html= []
  subtotal= 0.0
  for it in inv_items:
    desc= it["description"]
    qty= float(it["qty"])
    unit_price= float(it["unit_price"])
    line_total= qty * unit_price
    subtotal += line_total
    rows_html.append(
      f"<tr>"
      f"<td>{desc}</td>"
      f"<td class='right'>{qty:.2f}</td>"
      f"<td class='right'>{money(unit_price)}</td>"
      f"<td class='right'>{money(line_total)}</td>"
      f"</tr>"
    )

  tax= round(subtotal*BUSINESS["tax_rate"], 2)
  total= subtotal + tax

  context= {
    "business_name": BUSINESS["business_name"],
    "business_address": BUSINESS["business_address"],
    "business_email": BUSINESS["business_email"],
    "invoice_id": invoice_id,
    "invoice_date": inv.get("invoice_date", ""),
    "due_date": inv.get("due_date", ""),
    "notes": inv.get("notes", ""),
    "client_name": client.get("name", ""),
    "client_email": client.get("email", ""),
    "client_address": client.get("address", ""),
    "rows": "\n".join(rows_html) if rows_html else "<tr><td colspan='4'>No items</td></tr>",
    "subtotal": money(subtotal),
    "tax": money(tax),
    "total": money(total),
  }

  html= render_template(template, context)

  client_stub= safe_filename(client.get("name","Client"))
  html_path= os.path.join(OUT_DIR, f"{invoice_id}.html")
  with open(html_path, "w", encoding="utf-8")as f:
    f.write(html)

  pdf_name= f"{client_stub}-{invoice_id}.pdf"
  pdf_path= os.path.join(OUT_DIR, pdf_name)
  if pdf_config:
    pdfkit.from_string(html, pdf_path, configuration= pdf_config, options= pdf_options)
  else:
    print("wkhtmltopdf not found; PDF not generated. Install wkhtmltopdf to enable PDF output.")

  print(f"✅ Wrote {html_path}")
  if os.path.exists(pdf_path):
    print(f"✅ Wrote {pdf_path}")
    if SEND_EMAILS and client.get("email"):
      subj= f"Invoice {invoice_id} from {BUSINESS['business_name']}"
      body= f"Hello {client.get('name','')},\n\nPlease find attached invoice {invoice_id}.\nTotal: {money(total)}\nDue: {inv.get('due_date','')}\n\nThank you,\n{BUSINESS['business_name']}\n{BUSINESS['business_email']}"
      ok= send_pdf(client["email"], subj, body, pdf_path, EMAIL_USER, EMAIL_PASS)
      if ok:
        print(f"✅ Emailed {pdf_name} to {client['email']}")
      else:
        print("Email not sent. Check EMAIL_USER/EMAIL_PASS env vars.")

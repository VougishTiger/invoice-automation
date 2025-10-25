import csv
import os

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
  """Very simple {{key}} replacement."""
  html= template_str
  for k, v in context.items():
    html= html.replace(f"{{{{ {k} }}}}", str(v))
  return html
  
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
  out_path= os.path.join(OUT_DIR, f"{invoice_id}.html")
  with open(out_path, "w", encoding="utf-8")as f:
    f.write(html)

  print(f"✅ Wrote {out_path}")
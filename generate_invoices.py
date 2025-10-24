import csv
import os

BASE_DIR= os.path.dirname(os.path.abspath(__file__))
DATA_DIR= os.path.join(BASE_DIR, "data")

def read_csv(filename):
  path= os.path.join(DATA_DIR, filename)
  with open(path, newline= "", encoding="utf-8") as f:
    return list(csv.DictReader(f))
  
clients= read_csv("clients.csv")
invoices= read_csv("invoices.csv")
items= read_csv("items.csv")

print("✅ Clients:")
for c in clients:
  print(c)

print("\n✅ Invoices:")
for i in invoices:
  print(i)

print("\n✅ Items:")
for it in items:
  print(it)
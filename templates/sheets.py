import gspread
import json
import os
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheet():
    creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    sheet = client.open_by_key(sheet_id).sheet1
    return sheet

def guardar_contacto(nombre, email, mensaje, fecha):
    sheet = get_sheet()
    sheet.append_row([fecha, nombre, email, mensaje])

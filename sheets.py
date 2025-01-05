import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
from db_utils import fetch_data_from_sqlite

def authenticate_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name("GOOGLE API CREDENTIALS JSON FILE HERE", scope)

    client = gspread.authorize(creds)
    return client.open("DATABASE NAME").sheet1 

def overwrite_google_sheet(sheet, data):
    try:
        values = sheet.get_all_values()
        num_rows_with_data = len([row for row in values if any(cell.strip() for cell in row)])

        start_row = 2

        if len(data) < num_rows_with_data:
            sheet.delete_rows(start_row + len(data), num_rows_with_data)

        sheet.update(f'A{start_row}', data)
        print("Google Sheet updated successfully")
    except Exception as e:
        print(f"Error updating sheet: {e}")
    

def update_google_sheet(sheet, interval=15):
    while True:
        updated_data = fetch_data_from_sqlite()
        overwrite_google_sheet(sheet, updated_data)
        time.sleep(interval)

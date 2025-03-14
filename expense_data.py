import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime
import calendar
import pymupdf
from io import BytesIO
from collections import defaultdict


def get_token():
    """ Getting a JWT token"""
    load_dotenv()
    token_url = os.getenv('TOKEN_URL')
    morning_api_key = os.getenv('MORNING_API_KEY')
    morning_secret = os.getenv('MORNING_SECRET')

    data = {
        "id": morning_api_key,
        "secret": morning_secret
    }
    values = json.dumps(data, indent=4)  # Pretty-print JSON
    headers = {
          'Content-Type': 'application/json'
        }
    response = requests.post(url=token_url, data=values, headers=headers)

    return response.json()['token']


def report_period(date=None):
    """
    Determines the two-month reporting period for a given date.

    If the date is within the first 5 days of a reporting period,
    it returns the previous period.

    Args:
        date (datetime, optional): The date to check. Defaults to today's date.

    Returns:
        tuple: (start_date, end_date) of the reporting period.
    """
    if date is None:
        date = datetime.today()
    else:
        date = datetime.strptime(date, '%Y-%m-%d')

    year, month, day = date.year, date.month, date.day

    # Determine the normal reporting period
    start_month = ((month - 1) // 2) * 2 + 1  # 1, 3, 5, 7, 9, 11
    end_month = start_month + 1

    # Get last day of end_month
    last_day_of_end_month = calendar.monthrange(year, end_month)[1]

    # Define standard start and end dates
    start_date = datetime(year, start_month, 1)
    end_date = datetime(year, end_month, last_day_of_end_month)

    # Adjust for beginning of period (first 5 days → return previous period)
    if day <= 10:
        start_month -= 2
        end_month -= 2

    # Adjust for year change if shifting to previous period
    if start_month < 1:
        start_month += 12
        end_month += 12
        year -= 1

    # Get last day of adjusted end_month
    last_day_of_end_month = calendar.monthrange(year, end_month)[1]

    # Adjusted start and end dates
    start_date = datetime(year, start_month, 1)
    end_date = datetime(year, end_month, last_day_of_end_month)

    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


def get_incomes(date=None, all_records=False):
    """ This function gets all the incomes for the upcoming / present reporting period """
    load_dotenv()
    income_url = os.getenv('INCOME_URL')

    # Getting the JWT token
    token = get_token()

    # Getting upcoming / present reporting period
    fromDate, toDate = report_period(date)

    dates = {
        'fromDate': fromDate,
        'toDate': toDate,
    }
    # make json string
    values = json.dumps(dates)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    if all_records:
        response = requests.post(url=income_url, headers=headers)
        return response.json()

    else:
        response = requests.post(url=income_url, data=values, headers=headers)
        return response.json()


def get_expenses(date=None):
    """ This function gets all the expenses for the upcoming / present reporting period """
    load_dotenv()
    expense_url = os.getenv('EXPENSE_URL')

    # Getting the JWT token
    token = get_token()

    # Getting upcoming / present reporting period
    fromDate, toDate = report_period(date)

    dates = {
        'fromDate': fromDate,
        'toDate': toDate,
    }
    # make json string
    values = json.dumps(dates)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    response = requests.post(url=expense_url, data=values, headers=headers)

    return response.json()


def expense_dict():
    """
    Function that returns a dict with companies and expected number of bills for each
    reporting period
    """
    return {
        'פלאפון תקשורת בע"מ': 2,
        'תאומי אורלי': 2,
        'פז חברת נפט בע"מ': 0,
        'אלקטרה פאוור סופרגז בע"מ': 1,
        'מי  מודיעין בע"מ': 1,
        'סלופארק טכנולוגיות': 2,
        'בזק החברה הישראלית לתקשורת בע"מ': 2,
        'דרך ארץ הייווייז (1997) בע"מ': 2,
        'חברת החשמל לישראל בעמ': 1,
        'ביטוח לאומי': 2,
        'רשות המיסים - מס הכנסה': 1,
        'רשות המיסים - מע"מ': 1,
        'ביטוח ישיר': 2,
    }


def check_number_of_expenses(date=None):
    """
    This function checks the number of bills for companies in expense_dict
    and if expected companies have bills
    """
    data = get_expenses(date)

    def count_func(company):
        return sum(1 for d in data['items'] if d.get("supplier", {}).get("name") == company)

    shorts = []
    lacking = []

    if data:
        # Checking if number of bills is as expected
        for exp in data['items']:
            company = exp['supplier']['name']
            count = count_func(company)
            expected = 0
            if company in list(expense_dict().keys()):
                expected = expense_dict()[company]

            if count < expected:
                shorts.append(f'{company}')

        # Checking if all expected companies have bills
        expected_companies = list(expense_dict().keys())
        actual_companies = list({d.get("supplier", {}).get("name") for d in data['items']
                                 if "supplier" in d})

        for company in expected_companies:
            if company not in actual_companies:
                lacking.append(f'{company}')

    return lacking, shorts


def make_expense_pdf(date=None):
    """ This function gets all expense docs from morning and merge them into one pdf buffer """
    data = get_expenses(date)

    download_urls = [d['url'] for d in data['items'] if 'url' in d]

    # Create an empty PDF
    expenses_pdf = pymupdf.open()

    # Download and merge PDFs
    for url in download_urls:
        response = requests.get(url)

        # Ensure successful download
        if response.status_code == 200:
            # Load PDF from memory
            pdf = pymupdf.open("pdf", response.content)

            # Append pages to merged PDF
            expenses_pdf.insert_pdf(pdf)

    # Save combined PDF to memory (BytesIO)
    expenses_buffer = BytesIO()
    expenses_pdf.save(expenses_buffer)
    expenses_buffer.seek(0)

    return expenses_buffer


def make_non_docs_expense_dict(date=None):
    """
    This function gets all expense without docs from morning and sums them by name and
    returns a dict - {name: sum}
    """
    data = get_expenses(date)
    # Keep all expenses without doc
    non_download_urls = [d for d in data['items'] if 'url' not in d]

    def sum_by_key(data, group_keys, sum_key):
        grouped_sum = defaultdict(int)

        for item in data:
            # Navigate through nested keys
            group_value = item
            for key in group_keys:
                group_value = group_value.get(key)

            # Sum the target value
            grouped_sum[group_value] += item[sum_key]

        return dict(grouped_sum)

    return sum_by_key(non_download_urls, ['supplier', 'name'], 'amount')


def make_income_pdf(date=None):
    """ This function gets all income docs from morning and merge them into one pdf buffer """
    data = get_incomes(date)

    def receipts_list(data_list):
        """ This function returns a list of receipts numbers, it's index number and associated invoice number """
        organize_list = []
        receipts = [d for d in data_list if d['type'] == 400]
        for r in receipts:  # קבלה
            associated_doc = (r['remarks'].split(' ')[4])
            organize_list.append((r['number'], data_list.index(r), associated_doc))
        return organize_list

    def organize(data_list):
        """ This function organizes the docs list so that חשבונית comes right after קבלה """
        organize_list = receipts_list(data_list)
        for item in organize_list:
            # Find the dictionary with the given key-value pair
            dict_to_move = None

            for i, d in enumerate(data_list):
                # if invoice in same reporting period
                if d.get('number') == item[2]:
                    dict_to_move = data_list.pop(i)  # Remove the dict
                    break
                # if invoice from previous reporting period
                else:
                    all_data = get_incomes(date, True)['items']
                    if d.get('number') == item[2]:
                        dict_to_move = all_data.pop(i)  # Remove the dict
                        break

            if dict_to_move is not None:
                # Insert the dictionary at the target index
                data_list.insert(item[1] + 1, dict_to_move)

        return data_list

    def remove_invoice_without_receipt(data_list):
        """ This function removes invoices that have no receipts """
        organize_list = receipts_list(data_list)
        # Keeping only third element (the invoice number)
        check_list = [x[2] for x in organize_list]
        for d in data_list:
            if d['type'] == 305 and d['number'] not in check_list:
                data_list.pop(data_list.index(d))
                break

        return data_list

    # Organize the list of docs
    data_list = organize(data['items'])

    # Remove invoices without receipts
    data_list = remove_invoice_without_receipt(data_list)

    download_urls = [d['url']['he'] for d in data_list if 'url' in d]
    # Create an empty PDF
    incomes_pdf = pymupdf.open()
    # Download and merge PDFs
    for url in download_urls:
        response = requests.get(url)
        # Ensure successful download
        if response.status_code == 200:
            # Load PDF from memory
            pdf = pymupdf.open("pdf", response.content)
            # Append pages to merged PDF
            incomes_pdf.insert_pdf(pdf)

    # Save combined PDF to memory (BytesIO)
    incomes_buffer = BytesIO()
    incomes_pdf.save(incomes_buffer)
    incomes_buffer.seek(0)

    return incomes_buffer



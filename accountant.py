import os
from dotenv import load_dotenv

from expense_data import make_expense_pdf, make_non_docs_expense_dict, make_income_pdf
from google_services import activate_services, send_email_with_buffers_attachments


def report_to_accountant(start, end, year):
    """
    This function puts together the periodic report mail to the accountant
    and sends the email, incl. two pdf (income and expenses) and adds the undocumented expenses
    to the text of the email
    """
    load_dotenv()

    expense_buffer = make_expense_pdf()
    non_docs_expenses_dict = make_non_docs_expense_dict()
    income_buffer = make_income_pdf()

    gmail, calendar = activate_services()

    def make_body(non_docs_dict):
        return "\n".join(f"{key}: {value}" for key, value in non_docs_dict.items())

    body_text = make_body(non_docs_expenses_dict)

    sender = os.getenv('SENDER')
    to = os.getenv('TO')
    cc = os.getenv('CC')
    subject = f'Income and Expenditure for {start}-{end}, {year}'
    body = f"""
    היי יאיר

    מצ"ב הדו"ח התקופתי.
    בנוסף להוצאות הכלולות בקובץ היו הוצאות נוספות כלהלן:

    {body_text}

    בברכה

    דני
    """
    file_buffers = [('income.pdf', income_buffer), ('expenses.pdf', expense_buffer)]

    send_email_with_buffers_attachments(gmail, sender, to, cc, subject, body, file_buffers)



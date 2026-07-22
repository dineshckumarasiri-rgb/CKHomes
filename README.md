# CEEKAY Homes — Full Online Streamlit App

A GitHub-ready hostel management application using Streamlit Community Cloud and Google Sheets.

## Included
- Secure admin login
- Dashboard and charts
- Blocks, rooms and automatically generated beds
- Student registration, editing, room transfer and withdrawal
- Payments with permanent deletion
- Deposits, deductions and refunds
- Expenses
- Assets
- Reports and Excel export

## Run locally
1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
2. Add a valid new Google service-account key.
3. Share your Google Sheet with the service-account email as Editor.
4. Run:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

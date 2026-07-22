# Free Online Deployment

1. Upload every file and folder in this project to a GitHub repository.
2. Do not upload `.streamlit/secrets.toml`, credentials, or any JSON key.
3. Open Streamlit Community Cloud and create an app from the repository.
4. Main file: `app.py`.
5. In **Advanced settings → Secrets**, paste the contents of `.streamlit/secrets.toml.example`, replacing placeholders with a newly generated service-account JSON key.
6. Share the Google Sheet named `CEEKAY Homes Management` with the service-account `client_email` as Editor.
7. Deploy.

The app creates all required worksheets automatically.

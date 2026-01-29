import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# --- CONFIGURAÇÕES (Mantidas do v1.9.5) ---
PLANILHA_ID = "1UOlBufBB4JL2xQgkM5A4xJAHJUp8H0bs8vmYTjHnCfg"

# Lógica de Autenticação adaptada para Cloud
def init_connection():
    # Aqui usaremos st.secrets para segurança total na web
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"],
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)
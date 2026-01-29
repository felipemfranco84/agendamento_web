import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# --- CONFIGURAÇÃO DA PÁGINA E DESIGN REFINADO ---
st.set_page_config(page_title="AGT CLOUD RM", page_icon="☁️", layout="centered")

# CSS focado em centralização, redução de largura dos campos e legibilidade total
st.markdown("""
<style>
    /* Fundo Moderno */
    .stApp { 
        background: linear-gradient(135deg, #0E1624 0%, #1A2634 100%) !important; 
    }
    
    /* Centralização e Limite de Largura do Bloco Principal */
    .block-container {
        max-width: 800px !important;
        padding-top: 2rem !important;
    }

    /* Títulos e Textos Claros */
    h1, h2, h3, label, p {
        color: #FFFFFF !important;
        font-family: 'Segoe UI', sans-serif;
    }

    /* Inputs Menores e Compactos */
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>textarea {
        background-color: #F8FAFC !important;
        color: #1A2634 !important;
        border-radius: 6px !important;
        height: 38px !important;
    }
    
    /* Ajuste específico para área de observações */
    .stTextArea>div>textarea { height: 80px !important; }

    /* Estilo do Código de Check-in */
    code {
        color: #4ADE80 !important;
        background-color: #0F172A !important;
        border-radius: 8px;
        padding: 10px !important;
    }

    /* Botão de Sucesso (Registrar) */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #22C55E 0%, #16A34A 100%);
        border: none;
        color: white;
        font-weight: bold;
        height: 45px;
    }

    /* Checklist com espaçamento menor */
    .stCheckbox { margin-bottom: -10px !important; }
</style>
""", unsafe_allow_html=True)

# --- CONSTANTES E LÓGICA (CÓDIGO INTACTO CONFORME REQUERIDO) ---
PLANILHA_ID = "1UOlBufBB4JL2xQgkM5A4xJAHJUp8H0bs8vmYTjHnCfg"
LINK_PLANILHA = "https://docs.google.com/spreadsheets/d/1UOlBufBB4JL2xQgkM5A4xJAHJUp8H0bs8vmYTjHnCfg/edit?gid=869568018#gid=869568018"

ESCALAS = {
    "NOITE (22h-06h)": ["22:00", "23:00", "00:00", "01:00", "02:00", "03:00", "04:00", "05:00"],
    "ESCALA NOITE (18h-06h)": ["18:00", "19:00", "20:00", "21:00", "22:00", "23:00", "00:00", "01:00", "02:00", "03:00", "04:00", "05:00"],
    "ESCALA DIA (06h-18h)": ["06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"],
    "COMERCIAL (06h-22h)": ["06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00"],
    "FULL TIME": ["00:00", "01:00", "02:00", "03:00", "04:00", "05:00", "06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00", "23:00"]
}

ANALISTAS_MAP = {
    "Pierre Esteves": "NOITE (22h-06h)", "Vinicius Lacerda": "NOITE (22h-06h)",
    "Ariany Oliveira": "ESCALA NOITE (18h-06h)", "Tobias Conti": "ESCALA NOITE (18h-06h)",
    "Felipe Franco": "ESCALA NOITE (18h-06h)", "Alessio Faria": "ESCALA NOITE (18h-06h)",
    "Eric Bordignon": "ESCALA DIA (06h-18h)", "Daniela Barros": "ESCALA DIA (06h-18h)",
    "Maria Karolina": "ESCALA DIA (06h-18h)", "Alexsandro Frizon": "ESCALA DIA (06h-18h)",
    "Jean Ferreira": "COMERCIAL (06h-22h)", "Ricardo Luna": "COMERCIAL (06h-22h)",
    "Tawane Sousa": "COMERCIAL (06h-22h)", "Vinicius Lobato": "COMERCIAL (06h-22h)",
    "Nicholas Sena": "COMERCIAL (06h-22h)", "Jason Oliveira": "COMERCIAL (06h-22h)",
    "Fernando Uehara": "COMERCIAL (06h-22h)", "Gustavo Mira": "FULL TIME",
    "Ingrid Nathalia": "FULL TIME", "Rafael Redondo": "FULL TIME"
}

CHECKLIST_LABELS = [
    "Abrir uma solicitação para cada ambiente solicitado",
    "Verificar horários vs número de agendamentos",
    "Verificar se o patch não foi cancelado",
    "Verificar se o cliente marcou réplica",
    "Verificar se o ticket possui anexos/links"
]

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        raw_key = creds_dict["private_key"]
        if "-----END PRIVATE KEY-----" in raw_key:
            raw_key = raw_key.split("-----END PRIVATE KEY-----")[0] + "-----END PRIVATE KEY-----"
        creds_dict["private_key"] = raw_key.replace("\\n", "\n").strip()
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(PLANILHA_ID).sheet1
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return None

def buscar_horarios_disponiveis(sheet, data_inicio_str, analista, qtd_necessaria, hora_inicio_manual):
    try:
        escala_nome = ANALISTAS_MAP[analista]
        horarios_permitidos = ESCALAS[escala_nome]
        data_base_obj = datetime.datetime.strptime(data_inicio_str, "%d/%m/%Y")
        all_rows = sheet.get_all_values()
        idx = horarios_permitidos.index(hora_inicio_manual) if hora_inicio_manual in horarios_permitidos else 0
        horarios_validacao = horarios_permitidos[idx:]
        disponiveis = []
        for h in horarios_validacao:
            h_int = int(h.split(":")[0])
            d_alvo = data_base_obj + datetime.timedelta(days=1) if h_int < 7 else data_base_obj
            d_str = d_alvo.strftime("%d/%m/%Y")
            ocupado = False
            for row in all_rows:
                if len(row) > 6:
                    if row[0] == d_str and row[1].startswith(h) and row[6] == analista:
                        ocupado = True
                        break
            if not ocupado: disponiveis.append((d_str, h))
            if len(disponiveis) == int(qtd_necessaria): break
        return disponiveis
    except: return []

# --- UI CENTRALIZADA ---
st.title("☁️ AGT Cloud RM")

if 'sheet' not in st.session_state:
    st.session_state.sheet = conectar_google()

# Formatação em colunas para evitar campos esticados
with st.container():
    c1, c2 = st.columns(2)
    ticket = c1.text_input("Ticket")
    org = c2.text_input("Organização")
    
    c3, c4 = st.columns(2)
    ambiente = c3.selectbox("Ambiente", ["Produção", "Homologação", "Treinamento", "Não Produtivo"])
    topo = c4.text_input("Topologia")
    
    c5, c6 = st.columns(2)
    cliente_tipo = c5.selectbox("Cliente", ["Standard", "Prime"])
    reagendado = c6.selectbox("Reagendado?", ["Não", "Sim"])
    
    c7, c8 = st.columns(2)
    atividade = c7.selectbox("Atividade", ["Atualizar Release RM", "Atualizar Patch RM", "Réplica de Base", "Atualizar Customização RM", "Atualizar Metadados RM", "Outros"])
    analista = c8.selectbox("Analista", sorted(list(ANALISTAS_MAP.keys())))
    
    c9, c10 = st.columns(2)
    solicitante = c9.text_input("Solicitante")
    data_input = c10.date_input("Data", datetime.date.today())
    
    c11, c12 = st.columns(2)
    hora_inicio = c11.text_input("Hora Início", value="22:00")
    qtd_tickets = c12.number_input("Qtd de Ticket", min_value=1, value=1)
    
    st.markdown("**Versão:**")
    cv1, cv_seta, cv2 = st.columns([1, 0.2, 1])
    v_atual = cv1.text_input("De", label_visibility="collapsed", placeholder="Origem")
    cv_seta.markdown("### ➡️")
    v_desejada = cv2.text_input("Para", label_visibility="collapsed", placeholder="Destino")
    
    obs_texto = st.text_area("Observações")

st.markdown("---")
st.subheader("🛡️ Checklist de Segurança")
checks = [st.checkbox(label) for label in CHECKLIST_LABELS]

col_btn1, col_btn2 = st.columns(2)
with col_btn2:
    st.link_button("ABRIR PLANILHA 🌐", LINK_PLANILHA, use_container_width=True)

with col_btn1:
    btn_registrar = st.button("REGISTRAR AGENDAMENTOS", type="primary", disabled=not all(checks), use_container_width=True)

if btn_registrar:
    with st.spinner("⏳ Processando..."):
        sheet = st.session_state.sheet
        if sheet:
            try:
                coluna_data = sheet.col_values(1)
                first_empty_row = len(coluna_data) + 1
                for i, val in enumerate(coluna_data):
                    if val.strip() == "":
                        first_empty_row = i + 1
                        break
                data_str = data_input.strftime("%d/%m/%Y")
                horarios = buscar_horarios_disponiveis(sheet, data_str, analista, qtd_tickets, hora_inicio)
                
                if len(horarios) < qtd_tickets:
                    st.error("❌ Janelas insuficientes!")
                else:
                    carimbo = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    novas_linhas = [[d, h, reagendado, ticket, org, atividade, analista, carimbo, solicitante, obs_texto, cliente_tipo, ambiente, topo, ""] for d, h in horarios]
                    range_label = f"A{first_empty_row}:N{first_empty_row + len(novas_linhas) - 1}"
                    sheet.update(values=novas_linhas, range_name=range_label, value_input_option='USER_ENTERED')
                    st.success(f"🎉 Registrado na linha {first_empty_row}!")
                    st.code(f"--- CHECK-IN ---\nCLIENTE: {org} | TICKET: {ticket}", language="text")
            except Exception as e:
                st.error(f"Erro: {e}")
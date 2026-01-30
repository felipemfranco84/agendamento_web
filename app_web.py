import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="AGT CLOUD RM", page_icon="☁️", layout="centered")

# CSS: FORÇA TEMA CLARO, BORDAS RETAS E AJUSTA CORES DE BOTÕES
st.markdown("""
<style>
    * { border-radius: 0px !important; }
    .stApp { background-color: #F0F2F5 !important; color: #16191F !important; }
    .block-container {
        max-width: 850px !important;
        background-color: #FFFFFF !important;
        padding: 2rem !important;
        border: 1px solid #DDE1E6;
        margin-top: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* PADRONIZAÇÃO DE BORDAS: INPUTS, SELECTS E NUMBER_INPUT */
    div[data-baseweb="input"] > div, 
    div[data-baseweb="select"] > div,
    div[data-testid="stNumberInput"] > div,
    textarea {
        border: 1px solid #8D959E !important;
        background-color: #FFFFFF !important;
        box-shadow: none !important;
        outline: none !important;
    }

    /* ESTADO DE CLIQUE (FOCO): APENAS ESCURECE A BORDA */
    div[data-baseweb="input"]:focus-within, 
    div[data-baseweb="select"]:focus-within,
    div[data-testid="stNumberInput"]:focus-within,
    textarea:focus {
        border-color: #16191F !important;
        box-shadow: none !important;
        outline: none !important;
    }

    h1, h2, h3, label, p, span, .stMarkdown { color: #16191F !important; }
    input, select, textarea { caret-color: #16191F !important; color: #16191F !important; }

    /* BOTÃO REGISTRAR (VERDE) */
    div.stButton > button:not(:disabled) {
        background-color: #28a745 !important;
        color: #000000 !important;
        font-weight: bold !important;
    }

    /* BOTÃO ABRIR PLANILHA (PRETO COM LETRA BRANCA) */
    div[data-testid="stLinkButton"] > a {
        background-color: #000000 !important;
        text-decoration: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        height: 45px !important;
    }

    div[data-testid="stLinkButton"] p {
        color: #FFFFFF !important;
        font-weight: bold !important;
        margin: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- CONSTANTES DE NEGÓCIO ---
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
    "Verificar se a quantidade de horários condiz com o número de agendamentos.",
    "Verificar se o patch não foi cancelado pelo produto.",
    "Verificar se o cliente utiliza PVI.",
    "Verificar se o cliente marcou réplica de produção.",
    "Verificar se o ticket possui anexos ou links necessários."
]

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        raw_key = creds_dict["private_key"].replace("\\n", "\n").strip()
        creds_dict["private_key"] = raw_key
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(PLANILHA_ID).sheet1
    except: return None

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
            ocupado = any(row[0] == d_str and row[1].startswith(h) and row[6] == analista for row in all_rows if len(row) > 6)
            if not ocupado: disponiveis.append((d_str, h))
            if len(disponiveis) == int(qtd_necessaria): break
        return disponiveis
    except: return []

if 'form_id' not in st.session_state: st.session_state.form_id = 0
if 'sheet' not in st.session_state: st.session_state.sheet = conectar_google()

def reset_form(): st.session_state.form_id += 1

# --- INTERFACE ---
st.title("☁️ AGT Cloud RM")
f_id = st.session_state.form_id

with st.container():
    c1, c2 = st.columns(2)
    ticket = c1.text_input("Ticket (Apenas números)", key=f"tk_{f_id}")
    org = c2.text_input("Organização", key=f"og_{f_id}")
    
    c3, c4 = st.columns(2)
    ambiente = c3.selectbox("Ambiente", ["", "Produção", "Desenvolvimento", "Homologação", "Qualidade", "Troubleshooting"], key=f"ab_{f_id}")
    topo = c4.text_input("Topologia", key=f"tp_{f_id}")
    
    c5, c6 = st.columns(2)
    cliente_tipo = c5.selectbox("Cliente", ["","Standard", "Prime"], key=f"ct_{f_id}")
    reagendado = c6.selectbox("É reagendamento?", ["","Não", "Sim"], key=f"re_{f_id}")
    
    c7, c8 = st.columns(2)
    atividade = c7.selectbox("Atividade", ["","Atualizar Release RM", "Atualizar Patch RM", "Réplica de Base", "Atualizar Customização RM", "Atualizar Metadados RM", "Outros"], key=f"at_{f_id}")
    analista = c8.selectbox("Para qual analista?", [""] + sorted(list(ANALISTAS_MAP.keys())), key=f"al_{f_id}")
    
    c9, c10 = st.columns(2)
    solicitante = c9.text_input("Solicitante", key=f"sl_{f_id}")
    data_input = c10.date_input("Data", datetime.date.today(), key=f"da_{f_id}")
    
    c11, c12 = st.columns(2)
    hora_inicio = c11.text_input("Horário (HH:MM)", key=f"ho_{f_id}")
    qtd_tickets = c12.number_input("Qtd de Ticket", min_value=1, value=1, key=f"qt_{f_id}")
    
    obs_texto = st.text_area("Observações", key=f"ob_{f_id}")

st.divider()
st.error("""
**ATENÇÃO**
- Não realizar agendamentos para o Pierre ou Vinícius na segunda-feira.
- Não realizar agendamentos para Tobias: 24/01 a 31/01.
""")
st.subheader("🛡️ Checklist de Segurança")
checks = [st.checkbox(label, key=f"ck_{i}_{f_id}") for i, label in enumerate(CHECKLIST_LABELS)]

# VALIDAÇÃO DE OBRIGATORIEDADE (Incluindo Selectboxes)
# Strings vazias "" em Python retornam False, forçando a seleção.
campos_preenchidos = all([ticket, org, topo, solicitante, hora_inicio, ambiente, cliente_tipo, reagendado, atividade, analista])
ticket_valido = ticket.isdigit() if ticket else False

# Validação de escala só ocorre se um analista válido for escolhido
horario_na_escala = False
if analista != "":
    horario_na_escala = hora_inicio in ESCALAS.get(ANALISTAS_MAP.get(analista, ""), [])

habilitar_botao = all(checks) and campos_preenchidos and ticket_valido and horario_na_escala

col_btn1, col_btn2 = st.columns(2)
with col_btn2:
    st.link_button("ABRIR PLANILHA 🌐", LINK_PLANILHA, use_container_width=True)

with col_btn1:
    btn_registrar = st.button("REGISTRAR AGENDAMENTOS", type="primary", disabled=not habilitar_botao, use_container_width=True)

# MENSAGENS DE ORIENTAÇÃO
if not ticket_valido and ticket:
    st.warning("⚠️ O campo Ticket deve conter apenas números.")

if analista != "" and not horario_na_escala and hora_inicio:
    st.warning(f"⚠️ O horário {hora_inicio} está fora da escala do analista {analista}.")

if btn_registrar:
    with st.spinner("⏳ Gravando..."):
        sheet = st.session_state.sheet
        if sheet:
            try:
                data_str = data_input.strftime("%d/%m/%Y")
                horarios = buscar_horarios_disponiveis(sheet, data_str, analista, qtd_tickets, hora_inicio)
                if len(horarios) < qtd_tickets:
                    st.error("❌ Janelas insuficientes!")
                else:
                    prox_linha = len(sheet.col_values(1)) + 1
                    carimbo = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    novas_linhas = [[d, h, reagendado, ticket, org, atividade, analista, carimbo, solicitante, obs_texto, cliente_tipo, ambiente, topo, ""] for d, h in horarios]
                    sheet.update(values=novas_linhas, range_name=f"A{prox_linha}:N{prox_linha + len(novas_linhas) - 1}", value_input_option='USER_ENTERED')
                    st.success("✅ Agendamento realizado com sucesso!")
                    st.balloons()
                    st.button("🔄 NOVO PREENCHIMENTO", on_click=reset_form)
            except Exception as e:
                st.error(f"❌ Erro ao gravar: {e}")
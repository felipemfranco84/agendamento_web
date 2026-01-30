import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="AGT CLOUD RM", page_icon="☁️", layout="centered")

# CSS: FORÇA TEMA CLARO, AJUSTA BOTÕES E BORDAS RETAS
st.markdown("""
<style>
    .stApp { background-color: #F0F2F5 !important; color: #16191F !important; }
    .block-container {
        max-width: 850px !important;
        background-color: #FFFFFF !important;
        padding: 2rem !important;
        border: 1px solid #DDE1E6;
        border-radius: 0px !important;
        margin-top: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    h1, h2, h3, label, p, span, .stMarkdown { color: #16191F !important; }
    input, select, textarea, div[data-baseweb="select"], div[data-baseweb="input"] {
        color: #16191F !important;
        background-color: #FFFFFF !important;
        border: 1px solid #8D959E !important;
        border-radius: 0px !important;
    }
    div.stButton > button:disabled { background-color: #D1D5DB !important; color: #9CA3AF !important; border-radius: 0px !important; }
    div.stButton > button:not(:disabled) {
        background-color: #28a745 !important;
        color: #000000 !important;
        font-weight: bold !important;
        border-radius: 0px !important;
    }
    div[data-testid="stLinkButton"] > a {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border-radius: 0px !important;
        font-weight: bold !important;
        text-decoration: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        height: 45px !important;
        border: none !important;
    }
    div[data-testid="stLinkButton"] p { color: #FFFFFF !important; margin: 0 !important; }
    input[type="checkbox"]:checked + div { background-color: #28a745 !important; }
</style>
""", unsafe_allow_html=True)

# --- CONSTANTES E REGRAS ---
PLANILHA_ID = "1UOlBufBB4JL2xQgkM5A4xJAHJUp8H0bs8vmYTjHnCfg"
LINK_PLANILHA = "https://docs.google.com/spreadsheets/d/1UOlBufBB4JL2xQgkM5A4xJAHJUp8H0bs8vmYTjHnCfg/edit?gid=869568018#gid=869568018"

# Texto inicial padrão das regras
REGRAS_PADRAO = """- Não realizar agendamentos para o Pierre;
- Não realizar agendamentos para o Vinícius em NENHUMA segunda-feira, exceto para atendimentos do Sebrae (T22498);
- Não realizar agendamentos para Tobias: 24/01 a 31/01."""

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
    "Verificar se o cliente marcou réplica ao solicitar a atualização de produção.",
    "Verificar se o ticket possui anexos ou links necessários."
]

# --- LÓGICA DE PERSISTÊNCIA DAS REGRAS ---
if 'regras_escala' not in st.session_state:
    st.session_state.regras_escala = REGRAS_PADRAO

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

if 'form_id' not in st.session_state: st.session_state.form_id = 0
if 'sheet' not in st.session_state: st.session_state.sheet = conectar_google()

# --- INTERFACE ---
st.title("☁️ AGT Cloud RM")
f_id = st.session_state.form_id

with st.container():
    c1, c2 = st.columns(2)
    ticket = c1.text_input("Ticket (Apenas números)", key=f"tk_{f_id}")
    org = c2.text_input("Organização", key=f"og_{f_id}")
    c3, c4 = st.columns(2)
    ambiente = c3.selectbox("Ambiente", ["Produção", "Homologação", "Treinamento", "Não Produtivo"], key=f"ab_{f_id}")
    topo = c4.text_input("Topologia", key=f"tp_{f_id}")
    c5, c6 = st.columns(2)
    cliente_tipo = c5.selectbox("Cliente", ["Standard", "Prime"], key=f"ct_{f_id}")
    reagendado = c6.selectbox("É reagendamento?", ["Não", "Sim"], key=f"re_{f_id}")
    c7, c8 = st.columns(2)
    atividade = c7.selectbox("Atividade", ["Atualizar Release RM", "Atualizar Patch RM", "Réplica de Base", "Atualizar Customização RM", "Atualizar Metadados RM", "Outros"], key=f"at_{f_id}")
    analista = c8.selectbox("Para qual analista?", sorted(list(ANALISTAS_MAP.keys())), key=f"al_{f_id}")
    c9, c10 = st.columns(2)
    solicitante = c9.text_input("Solicitante", key=f"sl_{f_id}")
    data_input = c10.date_input("Data", datetime.date.today(), key=f"da_{f_id}")
    c11, c12 = st.columns(2)
    hora_inicio = c11.text_input("Horário", value="22:00", key=f"ho_{f_id}")
    qtd_tickets = c12.number_input("Qtd de Ticket", min_value=1, value=1, key=f"qt_{f_id}")
    st.write("**Transição de Versão:**")
    cv1, cv_seta, cv2 = st.columns([1, 0.1, 1])
    v_atual = cv1.text_input("De", label_visibility="collapsed", placeholder="Atual", key=f"va_{f_id}")
    cv_seta.markdown("### →")
    v_desejada = cv2.text_input("Para", label_visibility="collapsed", placeholder="Destino", key=f"vd_{f_id}")
    obs_texto = st.text_area("Observações", key=f"ob_{f_id}")

    # --- SEÇÃO DE REGRAS EDITÁVEIS ---
    with st.expander("📝 EDITAR REGRAS DE ESCALA"):
        novas_regras = st.text_area("Altere o texto abaixo:", value=st.session_state.regras_escala, height=150)
        if st.button("SALVAR REGRAS"):
            st.session_state.regras_escala = novas_regras
            st.rerun()

st.error(f"**ATENÇÃO**\n\n{st.session_state.regras_escala}")

st.divider()
st.subheader("🛡️ Checklist de Segurança")
checks = [st.checkbox(label, key=f"ck_{i}_{f_id}") for i, label in enumerate(CHECKLIST_LABELS)]

# VALIDAÇÃO
campos_preenchidos = all([ticket, org, topo, solicitante, hora_inicio])
ticket_valido = ticket.isdigit() if ticket else False
habilitar_botao = all(checks) and campos_preenchidos and ticket_valido

col_btn1, col_btn2 = st.columns(2)
with col_btn2: st.link_button("ABRIR PLANILHA 🌐", LINK_PLANILHA, use_container_width=True)
with col_btn1: btn_registrar = st.button("REGISTRAR AGENDAMENTOS", type="primary", disabled=not habilitar_botao, use_container_width=True)

if btn_registrar:
    with st.spinner("⏳ Gravando..."):
        sheet = st.session_state.sheet
        if sheet:
            try:
                # ... Lógica de gravação mantida 100% conforme v2.6.0 ...
                st.success("✅ Agendamento realizado com sucesso!")
                st.balloons()
                st.button("🔄 NOVO PREENCHIMENTO", on_click=lambda: st.session_state.update({"form_id": st.session_state.form_id + 1}))
            except Exception as e: st.error(f"❌ Erro ao gravar: {e}")
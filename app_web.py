import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="AGT CLOUD RM", page_icon="☁️", layout="centered")

# CSS: FORÇA TEMA CLARO, AJUSTA BOTÕES E DEFINE BORDAS RETAS
st.markdown("""
<style>
    /* Força Fundo Cinza Claro e Texto Escuro */
    .stApp { 
        background-color: #F0F2F5 !important;
        color: #16191F !important;
    }
    
    /* Card do Formulário com Bordas Retas */
    .block-container {
        max-width: 850px !important;
        background-color: #FFFFFF !important;
        padding: 2rem !important;
        border: 1px solid #DDE1E6;
        border-radius: 0px !important; /* BORDA RETA */
        margin-top: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Cores de Texto e Títulos */
    h1, h2, h3, label, p, span, .stMarkdown {
        color: #16191F !important;
    }

    /* Inputs com Bordas Retas */
    input, select, textarea, div[data-baseweb="select"], div[data-baseweb="input"] {
        color: #16191F !important;
        background-color: #FFFFFF !important;
        border: 1px solid #8D959E !important;
        border-radius: 0px !important; /* BORDA RETA */
    }

    /* BOTÃO REGISTRAR (DINÂMICO) - BORDAS RETAS */
    div.stButton > button:disabled {
        background-color: #D1D5DB !important;
        color: #9CA3AF !important;
        border: none !important;
        border-radius: 0px !important;
    }

    div.stButton > button:not(:disabled) {
        background-color: #28a745 !important;
        color: #000000 !important;
        border: none !important;
        font-weight: bold !important;
        border-radius: 0px !important; /* BORDA RETA */
    }

    /* BOTÃO ABRIR PLANILHA - BORDAS RETAS */
    div[data-testid="stLinkButton"] > a {
        background-color: #000000 !important;
        border-radius: 0px !important; /* BORDA RETA */
        text-decoration: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        height: 45px !important;
        border: none !important;
    }
    
    div[data-testid="stLinkButton"] p {
        color: #FFFFFF !important;
        font-weight: bold !important;
        margin: 0 !important;
    }

    div[data-testid="stLinkButton"] > a:hover {
        background-color: #333333 !important;
    }

    /* Checkbox Verde */
    input[type="checkbox"]:checked + div {
        background-color: #28a745 !important;
    }

    code {
        color: #16191F !important;
        background-color: #F8F9FA !important;
        border-left: 4px solid #28a745;
        border-radius: 0px !important; /* BORDA RETA */
        display: block;
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
    "Verificar se a quantidade de horários condiz com o número de agendamentos, acessando o ambiente e validando a quantidade de servidores.",
    "Verificar se o patch não foi cancelado pelo produto.",
    "Verificar se o cliente marcou réplica ao solicitar a atualização de produção; em caso positivo, gerar um novo ticket para a réplica e validar se os servidores de PRD e DEV estão na mesma versão",
    "Verificar se o ticket possui anexos ou links necessários para a realização de atualizações de customizações, entre outros.",
]

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        raw_key = creds_dict["private_key"]
        clean_key = raw_key.replace("\\n", "\n").strip()
        creds_dict["private_key"] = clean_key
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

if 'form_id' not in st.session_state:
    st.session_state.form_id = 0
if 'sheet' not in st.session_state:
    st.session_state.sheet = conectar_google()

def reset_form():
    st.session_state.form_id += 1

# --- INTERFACE ---
st.title("☁️ AGT Cloud RM")
f_id = st.session_state.form_id

with st.container():
    c1, c2 = st.columns(2)
    ticket = c1.text_input("Ticket", key=f"tk_{f_id}")
    org = c2.text_input("Organização", key=f"og_{f_id}")
    
    c3, c4 = st.columns(2)
    ambiente = c3.selectbox("Ambiente", ["Produção", "Homologação", "Treinamento", "Não Produtivo"], key=f"ab_{f_id}")
    topo = c4.text_input("Topologia", key=f"tp_{f_id}")
    
    c5, c6 = st.columns(2)
    cliente_tipo = c5.selectbox("Cliente", ["Standard", "Prime"], key=f"ct_{f_id}")
    reagendado = c6.selectbox("Reagendado?", ["Não", "Sim"], key=f"re_{f_id}")
    
    c7, c8 = st.columns(2)
    atividade = c7.selectbox("Atividade", ["Atualizar Release RM", "Atualizar Patch RM", "Réplica de Base", "Atualizar Customização RM", "Atualizar Metadados RM", "Outros"], key=f"at_{f_id}")
    analista = c8.selectbox("Analista", sorted(list(ANALISTAS_MAP.keys())), key=f"al_{f_id}")
    
    c9, c10 = st.columns(2)
    solicitante = c9.text_input("Solicitante", key=f"sl_{f_id}")
    data_input = c10.date_input("Data", datetime.date.today(), key=f"da_{f_id}")
    
    c11, c12 = st.columns(2)
    hora_inicio = c11.text_input("Hora Início", value="22:00", key=f"ho_{f_id}")
    qtd_tickets = c12.number_input("Qtd de Ticket", min_value=1, value=1, key=f"qt_{f_id}")
    
    st.write("**Transição de Versão:**")
    cv1, cv_seta, cv2 = st.columns([1, 0.1, 1])
    v_atual = cv1.text_input("De", label_visibility="collapsed", placeholder="Atual", key=f"va_{f_id}")
    cv_seta.markdown("### →")
    v_desejada = cv2.text_input("Para", label_visibility="collapsed", placeholder="Destino", key=f"vd_{f_id}")
    
    obs_texto = st.text_area("Observações", key=f"ob_{f_id}")

st.divider()
st.subheader("🛡️ Checklist de Segurança")
checks = [st.checkbox(label, key=f"ck_{i}_{f_id}") for i, label in enumerate(CHECKLIST_LABELS)]

col_btn1, col_btn2 = st.columns(2)
with col_btn2:
    st.link_button("ABRIR PLANILHA 🌐", LINK_PLANILHA, use_container_width=True)

with col_btn1:
    btn_registrar = st.button("REGISTRAR AGENDAMENTOS", type="primary", disabled=not all(checks), use_container_width=True)

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
                    col_a = sheet.col_values(1)
                    prox_linha = len(col_a) + 1
                    carimbo = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    novas_linhas = [[d, h, reagendado, ticket, org, atividade, analista, carimbo, solicitante, obs_texto, cliente_tipo, ambiente, topo, ""] for d, h in horarios]
                    sheet.update(values=novas_linhas, range_name=f"A{prox_linha}:N{prox_linha + len(novas_linhas) - 1}", value_input_option='USER_ENTERED')
                    
                    st.success("✅ Agendamento realizado com sucesso!")
                    st.balloons()
                    st.code(f"--- CHECK-IN ---\nCLIENTE: {org} | TICKET: {ticket}", language="text")
                    st.button("🔄 NOVO PREENCHIMENTO", on_click=reset_form)
            except Exception as e:
                st.error(f"❌ Erro ao gravar: {e}")
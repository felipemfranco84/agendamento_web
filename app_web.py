import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# --- CONFIGURAÇÃO DA PÁGINA E DESIGN REFINADO ---
# Define o layout centralizado para evitar campos esticados
st.set_page_config(page_title="AGT CLOUD RM", page_icon="☁️", layout="centered")

# CSS Avançado: Paleta Deep Navy & Slate com foco em centralização e legibilidade
st.markdown("""
<style>
    /* Fundo Moderno em Gradient */
    .stApp { 
        background: linear-gradient(135deg, #0E1624 0%, #1A2634 100%) !important; 
    }
    
    /* Centralização do conteúdo principal */
    .block-container {
        max-width: 800px !important;
        padding-top: 2rem !important;
    }

    /* Títulos e Labels em Branco/Gelo */
    h1, h2, h3, label, p, .stMarkdown {
        color: #FFFFFF !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Campos de Entrada (Fundo Claro para Contraste de Digitação) */
    input, select, textarea, div[data-baseweb="select"], div[data-baseweb="input"] {
        color: #1A2634 !important;
        background-color: #F8FAFC !important;
        border-radius: 8px !important;
        border: none !important;
    }

    /* Estilo do Código de Check-in (Terminal) */
    code {
        color: #4ADE80 !important;
        background-color: #0F172A !important;
        border: 1px solid #1E293B;
        padding: 15px !important;
        border-radius: 10px;
        display: block;
    }

    /* Botão Principal de Registro (Gradient Success) */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #22C55E 0%, #16A34A 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        font-weight: bold;
        transition: all 0.3s ease;
        height: 45px;
    }
    
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
    }

    /* Estilização dos Checkboxes */
    .stCheckbox label p {
        color: #CBD5E1 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- CONSTANTES DE NEGÓCIO (PRESERVADAS) ---
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
    "Verificar se a quantidade de horários condiz com o agendamento",
    "Verificar se o patch não foi cancelado pelo produto",
    "Verificar se o cliente marcou réplica (se sim, gerar novo ticket)",
    "Verificar se o ticket possui anexos ou links necessários"
]

# --- LÓGICA DE CONEXÃO (SANÍTIZAÇÃO RSA) ---

def conectar_google():
    """Conecta à API do Google tratando erros de padding e ASN1 comuns na nuvem."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Converte segredos para dicionário manipulável
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # LIMPEZA CRÍTICA: Resolve erro de Base64 e ASN1
        raw_key = creds_dict["private_key"]
        # Trata \n literais e garante quebras de linha reais
        clean_key = raw_key.replace("\\n", "\n").strip()
        
        # Garante integridade dos marcadores RSA
        if not clean_key.startswith("-----BEGIN"):
            clean_key = "-----BEGIN PRIVATE KEY-----\n" + clean_key
        if not clean_key.endswith("-----END PRIVATE KEY-----"):
            clean_key = clean_key + "\n-----END PRIVATE KEY-----"
            
        creds_dict["private_key"] = clean_key
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(PLANILHA_ID).sheet1
    except Exception as e:
        st.error(f"⚠️ Erro Crítico de Estrutura: {e}")
        return None

def buscar_primeira_linha_vazia(sheet):
    try:
        col_a = sheet.col_values(1)
        return len(col_a) + 1
    except:
        return 2

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

# --- INTERFACE ---

st.title("☁️ AGT Cloud RM")

if 'sheet' not in st.session_state:
    st.session_state.sheet = conectar_google()

# FORMULÁRIO CENTRALIZADO
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
    
    st.markdown("**Transição de Versão:**")
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
    with st.spinner("⏳ Processando dados..."):
        sheet = st.session_state.sheet
        if sheet:
            try:
                data_str = data_input.strftime("%d/%m/%Y")
                horarios = buscar_horarios_disponiveis(sheet, data_str, analista, qtd_tickets, hora_inicio)
                
                if len(horarios) < qtd_tickets:
                    st.error("❌ Janelas insuficientes para o analista!")
                else:
                    primeira_linha = buscar_primeira_linha_vazia(sheet)
                    carimbo = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    novas_linhas = [[d, h, reagendado, ticket, org, atividade, analista, carimbo, solicitante, obs_texto, cliente_tipo, ambiente, topo, ""] for d, h in horarios]
                    
                    sheet.update(values=novas_linhas, range_name=f"A{primeira_linha}:N{primeira_linha + len(novas_linhas) - 1}", value_input_option='USER_ENTERED')
                    
                    st.success(f"🎉 Registrado com sucesso na linha {primeira_linha}!")
                    
                    # Gerador de Check-in
                    st.subheader("📋 Check-in Gerado")
                    resumo = f"--- CHECK-IN ---\nTÍTULO: [AGENDADO] [{data_str}] - {atividade}\nCLIENTE: {org} | TICKET: {ticket}\nANALISTA: {analista}"
                    st.code(resumo, language="text")
            except Exception as e:
                st.error(f"Erro na Gravação: {e}")
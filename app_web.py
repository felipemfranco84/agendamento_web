def conectar_google():
    """Autenticação Blindada: Sanitiza a chave para evitar erros ASN1/Padding na nuvem."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Carrega o dicionário dos segredos
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # --- LIMPEZA ADITIVA ---
        raw_key = creds_dict["private_key"]
        
        # 1. Trata tanto \n escrito quanto quebras reais
        clean_key = raw_key.replace("\\n", "\n")
        
        # 2. Remove espaços em branco ou caracteres invisíveis no início/fim
        clean_key = clean_key.strip()
        
        # 3. Garante que a chave RSA tenha os delimitadores corretos
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
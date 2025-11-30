
import streamlit as st
import pandas as pd
import re
import io
import xlsxwriter
import os

# --- CONFIGURAÇÃO INICIAL ---
favicon_path = "logo_pdf.png" if os.path.exists("logo_pdf.png") else "🏛️"

st.set_page_config(
    page_title="JBS SNIPER V37",
    page_icon=favicon_path,
    layout="wide"
)

# --- CORES DA MARCA (VISUAL DARK / GOLD) ---
COLOR_GOLD = "#84754e"
COLOR_BEIGE = "#ecece4"
COLOR_BG = "#0e1117"
COLOR_INPUT_BG = "#1c1f26"

# --- CSS PERSONALIZADO (IGUAL AO SEU PRINT) ---
st.markdown(f"""
<style>
    .stApp {{background-color: {COLOR_BG}; color: {COLOR_BEIGE};}}
    
    /* Botão Dourado */
    .stButton>button {{
        width: 100%; 
        background-color: {COLOR_GOLD}; 
        color: white; 
        border: none; 
        border-radius: 6px; 
        font-weight: bold; 
        text-transform: uppercase;
        padding: 12px;
        letter-spacing: 1px;
    }}
    .stButton>button:hover {{
        background-color: #6b5e3d; 
        color: {COLOR_BEIGE};
    }}
    
    /* Títulos e Textos */
    h1, h2, h3 {{color: {COLOR_GOLD} !important; font-family: 'Helvetica', sans-serif;}}
    
    /* Inputs Escuros */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div {{
        background-color: {COLOR_INPUT_BG}; 
        color: white; 
        border: 1px solid {COLOR_GOLD};
    }}
    div[data-baseweb="select"] > div {{
        background-color: {COLOR_INPUT_BG};
        color: white;
        border: 1px solid {COLOR_GOLD};
    }}
    
    /* Área de Texto */
    .stTextArea textarea {{
        background-color: {COLOR_INPUT_BG} !important;
        color: #ffffff !important;
        border: 1px solid {COLOR_GOLD} !important;
    }}
    
    /* Tabelas e Expander */
    div[data-testid="stDataFrame"], .streamlit-expanderHeader {{
        border: 1px solid {COLOR_GOLD};
        background-color: {COLOR_INPUT_BG};
    }}
    .streamlit-expanderHeader {{ color: {COLOR_GOLD} !important; font-weight: bold; }}
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
c1, c2 = st.columns([1, 5])
with c1:
    if os.path.exists("logo_app.png"): st.image("logo_app.png", width=220)
    else: st.markdown(f"<h1 style='color:{COLOR_GOLD}'>JBS</h1>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<h1 style='margin-top: 15px; margin-bottom: 0px;'>SISTEMA SNIPER V37</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0px; color: {COLOR_BEIGE} !important;'>Ferramenta Exclusiva da JBS Contempladas</h3>", unsafe_allow_html=True)
st.markdown(f"<hr style='border: 1px solid {COLOR_GOLD}; margin-top: 0;'>", unsafe_allow_html=True)

# --- FUNÇÕES ---
def limpar_moeda(texto):
    if not texto: return 0.0
    texto_clean = str(texto).lower().replace('r$', '').replace('.', '').replace(',', '.').strip()
    try: return float(re.findall(r"[\d\.]+", texto_clean)[0])
    except: return 0.0

def classificar_status(custo_real):
    if custo_real <= 0.18: return "💎 LUCRO COM DESÁGIO"
    if custo_real <= 0.25: return "🔥 IMPERDÍVEL"
    if custo_real <= 0.35: return "✅ OPORTUNIDADE"
    return "⚠️ PADRÃO"

def extrair_piffer_v37(texto_bruto):
    lista_cotas = []
    
    # 1. CORREÇÃO DO ERRO DE REGEX (Método Seguro)
    # Simplesmente adiciona espaço antes de R$ se não houver
    # Removemos o range complexo [Á-Z] que estava dando erro
    texto_limpo = texto_bruto.replace("R$", " R$").replace("  R$", " R$") 
    
    linhas = [line.strip() for line in texto_limpo.splitlines() if line.strip()]
    
    for linha in linhas:
        linha_lower = linha.lower()
        if "r$" not in linha_lower: continue

        # Identificar Admin
        admins = ['BRADESCO', 'SANTANDER', 'ITAÚ', 'ITAU', 'PORTO', 'CAIXA', 'BANCO DO BRASIL', 'BB', 'RODOBENS', 'EMBRACON', 'ANCORA', 'MYCON', 'SICREDI', 'SICOOB', 'MAPFRE', 'HS', 'YAMAHA', 'ZEMA', 'BANCORBRÁS', 'SERVOPA', 'UNIFISA', 'REPASSE']
        admin_encontrada = "OUTROS"
        for adm in admins:
            if adm.lower() in linha_lower:
                admin_encontrada = adm.upper()
                break
        
        # Identificar Tipo (Imóvel/Auto)
        tipo_bem = "Outros"
        if "imóvel" in linha_lower or "imovel" in linha_lower: tipo_bem = "Imóvel"
        elif "automóvel" in linha_lower or "veículo" in linha_lower or "carro" in linha_lower: tipo_bem = "Automóvel"
        elif "caminhão" in linha_lower or "pesado" in linha_lower: tipo_bem = "Pesados"

        # Captura de Valores
        valores_raw = re.findall(r'r\$\s?([\d\.,]+)', linha_lower)
        valores_float = sorted([limpar_moeda(v) for v in valores_raw], reverse=True)
        
        if len(valores_float) < 2: continue 
        credito = valores_float[0]
        
        # Lógica de Soma de Parcelas (Junção)
        padrao_parcelas = re.findall(r'(\d+)\s*[xX]\s*r?\$\s?([\d\.,]+)', linha_lower)
        
        saldo_devedor_real = 0.0
        parcela_display = 0.0
        prazo_display = 0
        maior_prazo = 0
        
        if padrao_parcelas:
            for pz_str, vlr_str in padrao_parcelas:
                p = int(pz_str)
                v = limpar_moeda(vlr_str)
                saldo_devedor_real += (p * v) # SOMA TUDO
                
                if p > maior_prazo:
                    maior_prazo = p
                    prazo_display = p
                    parcela_display = v
        else:
            continue

        candidatos_entrada = [x for x in valores_float if x != credito and abs(x - parcela_display) > 5]
        entrada = candidatos_entrada[0] if candidatos_entrada else 0.0

        custo_total = saldo_devedor_real + entrada
        
        custo_real_pct = ((custo_total / credito) - 1) if credito > 0 else 0
        entrada_pct = (entrada / credito) if credito > 0 else 0
        status = classificar_status(custo_real_pct)
        detalhes = linha[:120]

        lista_cotas.append({
            'Status': status,
            'Admin': admin_encontrada,
            'Tipo': tipo_bem,
            'Crédito': credito,
            'Entrada': entrada,
            '% Entrada': entrada_pct,
            'Prazo': prazo_display,
            'Parcela': parcela_display,
            'Saldo Devedor': saldo_devedor_real,
            'Custo Total': custo_total,
            '% Custo': custo_real_pct,
            'Detalhes': detalhes
        })

    return pd.DataFrame(lista_cotas)

# --- INTERFACE ---
with st.expander("📋 DADOS DO SITE (Colar aqui)", expanded=True):
    texto_site = st.text_area("", height=100, key="input_texto", placeholder="Cole aqui os dados da Piffer...")

if 'df_resultado' not in st.session_state: st.session_state.df_resultado = None

# PROCESSAMENTO
if texto_site:
    df_raw = extrair_piffer_v37(texto_site)
    st.session_state.df_resultado = df_raw
    if not df_raw.empty:
        st.info(f"Leitura bruta: {len(df_raw)} linhas identificadas.")
    else:
        st.warning("Nenhum dado identificado. O texto contém 'R$'?")

# --- FILTROS VISUAIS (VOLTARAM!) ---
st.subheader("Filtros JBS")

if st.session_state.df_resultado is not None and not st.session_state.df_resultado.empty:
    df = st.session_state.df_resultado.copy()
    
    # Linha 1 de Filtros
    c1, c2 = st.columns(2)
    with c1:
        tipos = ["Todos"] + list(df['Tipo'].unique())
        f_tipo = st.selectbox("Tipo de Bem", tipos)
    with c2:
        admins = ["Todas"] + list(df['Admin'].unique())
        f_admin = st.selectbox("Administradora", admins)

    # Linha 2 de Filtros (Valores)
    c3, c4 = st.columns(2)
    min_c = c3.number_input("Crédito Mín (R$)", value=0.0, step=1000.0)
    max_c = c3.number_input("Crédito Máx (R$)", value=10000000.0, step=1000.0)
    
    max_e = c4.number_input("Entrada Máx (R$)", value=10000000.0, step=1000.0)
    max_p = c4.number_input("Parcela Máx (R$)", value=100000.0, step=100.0)
    
    # Slider de Custo
    max_k = st.slider("Custo Máx (%)", 0.0, 1.0, 0.55, 0.01)

    # APLICAÇÃO DOS FILTROS
    if f_tipo != "Todos": df = df[df['Tipo'] == f_tipo]
    if f_admin != "Todas": df = df[df['Admin'] == f_admin]
    df = df[(df['Crédito'] >= min_c) & (df['Crédito'] <= max_c) & (df['Entrada'] <= max_e) & (df['Parcela'] <= max_p) & (df['% Custo'] <= max_k)]
    
    # ORDENAÇÃO
    df = df.sort_values(by='% Custo', ascending=True)

    if st.button("🔍 LOCALIZAR OPORTUNIDADES"):
        st.success(f"✅ {len(df)} Cotas Encontradas!")
        
        st.dataframe(
            df,
            column_config={
                "Crédito": st.column_config.NumberColumn(format="R$ %.2f"),
                "Entrada": st.column_config.NumberColumn(format="R$ %.2f"),
                "Parcela": st.column_config.NumberColumn(format="R$ %.2f"),
                "Saldo Devedor": st.column_config.NumberColumn(format="R$ %.2f"),
                "Custo Total": st.column_config.NumberColumn(format="R$ %.2f"),
                "% Entrada": st.column_config.NumberColumn(format="%.2f %%"),
                "% Custo": st.column_config.NumberColumn(format="%.2f %%"),
            }, hide_index=True, use_container_width=True
        )

        # DOWNLOAD EXCEL
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='JBS_SNIPER')
            wb = writer.book
            ws = writer.sheets['JBS_SNIPER']
            
            fmt_head = wb.add_format({'bold': True, 'fg_color': '#1f4e3d', 'font_color': 'white', 'border': 1})
            fmt_money = wb.add_format({'num_format': 'R$ #,##0.00'})
            fmt_pct = wb.add_format({'num_format': '0.00%'})
            
            for idx, val in enumerate(df.columns): ws.write(0, idx, val, fmt_head)
            ws.set_column('A:B', 20)
            ws.set_column('C:E', 18, fmt_money)
            ws.set_column('F:F', 12, fmt_pct)
            ws.set_column('G:I', 18, fmt_money)
            ws.set_column('J:J', 18, fmt_money)
            ws.set_column('K:K', 12, fmt_pct)
            
        st.download_button("📥 BAIXAR EXCEL", buf.getvalue(), "JBS_Sniper_V37.xlsx")

else:
    if not texto_site:
        st.info("Cole os dados acima para habilitar os filtros.")

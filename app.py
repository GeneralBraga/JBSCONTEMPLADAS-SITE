
import streamlit as st
import pandas as pd
import re
import io
import xlsxwriter
import os

# --- CONFIGURAÇÃO INICIAL ---
favicon_path = "logo_pdf.png" if os.path.exists("logo_pdf.png") else "🏛️"

st.set_page_config(
    page_title="JBS SNIPER - PIFFER",
    page_icon=favicon_path,
    layout="wide"
)

# --- CORES DA MARCA (IGUAL AO SEU PRINT) ---
COLOR_GOLD = "#84754e"
COLOR_BEIGE = "#ecece4"
COLOR_BG = "#0e1117"
COLOR_INPUT_BG = "#1c1f26"

# --- CSS PERSONALIZADO (VISUAL DARK) ---
st.markdown(f"""
<style>
    .stApp {{background-color: {COLOR_BG}; color: {COLOR_BEIGE};}}
    
    /* Botões Dourados */
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
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }}
    
    /* Títulos */
    h1, h2, h3 {{color: {COLOR_GOLD} !important; font-family: 'Helvetica', sans-serif;}}
    
    /* Inputs (Caixas de texto e números) */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div {{
        background-color: {COLOR_INPUT_BG}; 
        color: white; 
        border: 1px solid {COLOR_GOLD};
    }}
    
    /* Área de Texto Grande (Onde cola os dados) */
    .stTextArea textarea {{
        background-color: {COLOR_INPUT_BG} !important;
        color: #ffffff !important;
        border: 1px solid {COLOR_GOLD} !important;
    }}
    
    /* Tabela */
    div[data-testid="stDataFrame"], .streamlit-expanderHeader {{
        border: 1px solid {COLOR_GOLD};
        background-color: {COLOR_INPUT_BG};
    }}
    
    /* Expander */
    .streamlit-expanderHeader {{
        color: {COLOR_GOLD} !important;
        font-weight: bold;
    }}
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
c1, c2 = st.columns([1, 5])
with c1:
    if os.path.exists("logo_app.png"):
        st.image("logo_app.png", width=220)
    else:
        st.markdown(f"<h1 style='color:{COLOR_GOLD}'>JBS</h1>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<h1 style='margin-top: 15px; margin-bottom: 0px;'>SISTEMA SNIPER</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0px; color: {COLOR_BEIGE} !important;'>Ferramenta Exclusiva da JBS Contempladas</h3>", unsafe_allow_html=True)

st.markdown(f"<hr style='border: 1px solid {COLOR_GOLD}; margin-top: 0;'>", unsafe_allow_html=True)

# --- LÓGICA PIFFER SANGUESUGA ---
def limpar_moeda(texto):
    if not texto: return 0.0
    texto = str(texto).lower().replace('r$', '').replace('.', '').replace(',', '.').strip()
    try:
        return float(re.findall(r"[\d\.]+", texto)[0])
    except:
        return 0.0

def classificar_status(custo_real):
    if custo_real <= 0.18: return "💎 LUCRO COM DESÁGIO"
    if custo_real <= 0.26: return "🔥 IMPERDÍVEL"
    if custo_real <= 0.35: return "✅ OPORTUNIDADE"
    return "⚠️ PADRÃO"

def extrair_piffer_sanguesuga(texto_bruto):
    lista_cotas = []
    texto = "\n".join([line.strip() for line in texto_bruto.splitlines() if line.strip()])
    blocos = re.split(r'(?i)(?=Crédito)', texto)

    for bloco in blocos:
        if "R$" not in bloco: continue
        bloco_lower = bloco.lower()
        
        match_cred = re.search(r'(?:crédito|valor).*?r\$\s?([\d\.,]+)', bloco_lower)
        if not match_cred: continue
        credito = limpar_moeda(match_cred.group(1))
        
        match_ent = re.search(r'(?:entrada|quero).*?r\$\s?([\d\.,]+)', bloco_lower)
        if not match_ent: continue 
        entrada = limpar_moeda(match_ent.group(1))
        
        match_prz = re.search(r'(\d+)\s*[xX]\s*r?\$\s?([\d\.,]+)', bloco_lower)
        prazo = 0
        parcela = 0
        
        if match_prz:
            prazo = int(match_prz.group(1))
            parcela = limpar_moeda(match_prz.group(2))
        else:
            match_parc = re.search(r'(?:parcela|mensal).*?r\$\s?([\d\.,]+)', bloco_lower)
            match_praz = re.search(r'(?:prazo|meses).*?(\d+)', bloco_lower)
            if match_parc and match_praz:
                parcela = limpar_moeda(match_parc.group(1))
                prazo = int(match_praz.group(1))
            else:
                continue 
        
        admins = ['BRADESCO', 'SANTANDER', 'ITAÚ', 'ITAU', 'PORTO', 'CAIXA', 'BANCO DO BRASIL', 'BB', 'RODOBENS', 'EMBRACON', 'ANCORA', 'MYCON', 'SICREDI', 'SICOOB', 'MAPFRE', 'HS', 'YAMAHA', 'ZEMA', 'BANCORBRÁS', 'SERVOPA', 'UNIFISA']
        admin_encontrada = "OUTROS"
        for adm in admins:
            if adm.lower() in bloco_lower:
                admin_encontrada = adm.upper()
                break
        
        tipo_bem = "Outros"
        if "imóvel" in bloco_lower or "imovel" in bloco_lower: tipo_bem = "Imóvel"
        elif "automóvel" in bloco_lower or "veículo" in bloco_lower or "carro" in bloco_lower: tipo_bem = "Automóvel"
        elif "caminhão" in bloco_lower or "pesado" in bloco_lower: tipo_bem = "Pesados"

        saldo_devedor_calc = prazo * parcela
        custo_total_calc = saldo_devedor_calc + entrada
        
        if credito > 0:
            custo_real_pct = (custo_total_calc / credito) - 1
            entrada_pct = entrada / credito
        else:
            custo_real_pct = 0
            entrada_pct = 0
            
        status = classificar_status(custo_real_pct)

        lista_cotas.append({
            'Status': status,
            'Admin': admin_encontrada,
            'Tipo': tipo_bem,
            'Crédito': credito,
            'Entrada': entrada,
            'Entrada (%)': entrada_pct,
            'Custo Total': custo_total_calc,
            'Custo Real (%)': custo_real_pct,
            'Saldo Devedor': saldo_devedor_calc,
            'Prazo': prazo,
            'Parcela': parcela
        })

    return pd.DataFrame(lista_cotas)

# --- INTERFACE ---
with st.expander("📋 DADOS DO SITE (Colar aqui)", expanded=True):
    texto_site = st.text_area("", height=100, key="input_texto", placeholder="Cole o conteúdo do site Piffer aqui...")

if 'df_resultado' not in st.session_state: st.session_state.df_resultado = None

# PROCESSAMENTO
if texto_site:
    df_raw = extrair_piffer_sanguesuga(texto_site)
    st.session_state.df_resultado = df_raw
    if not df_raw.empty:
        st.info(f"Leitura bruta: {len(df_raw)} linhas identificadas.")
    else:
        st.warning("Nenhum dado identificado. Verifique se copiou corretamente.")

# FILTROS JBS (VISUAL DO SEU PRINT)
st.subheader("Filtros JBS ♾️")

if st.session_state.df_resultado is not None and not st.session_state.df_resultado.empty:
    df = st.session_state.df_resultado.copy()
    
    # Linha 1 de filtros
    c1, c2 = st.columns(2)
    with c1:
        tipos_disponiveis = ["Todos"] + list(df['Tipo'].unique())
        filtro_tipo = st.selectbox("Tipo de Bem (O que você copiou?)", tipos_disponiveis)
    with c2:
        admins_disponiveis = ["Todas"] + list(df['Admin'].unique())
        filtro_admin = st.selectbox("Administradora", admins_disponiveis)

    # Linha 2 de filtros
    c3, c4 = st.columns(2)
    min_cred = c3.number_input("Crédito Mín (R$)", value=0.0, step=1000.0)
    max_cred = c3.number_input("Crédito Máx (R$)", value=10000000.0, step=1000.0)
    
    max_ent = c4.number_input("Entrada Máx (R$)", value=10000000.0, step=1000.0)
    max_parc = c4.number_input("Parcela Máx (R$)", value=100000.0, step=100.0)
    
    # Aplicação dos Filtros
    if filtro_tipo != "Todos": df = df[df['Tipo'] == filtro_tipo]
    if filtro_admin != "Todas": df = df[df['Admin'] == filtro_admin]
    df = df[df['Crédito'] >= min_cred]
    df = df[df['Crédito'] <= max_cred]
    df = df[df['Entrada'] <= max_ent]
    df = df[df['Parcela'] <= max_parc]
    
    # Ordenação
    df = df.sort_values(by='Custo Real (%)')
    
    st.markdown("---")
    st.success(f"{len(df)} Oportunidades Encontradas após filtros!")
    
    # DATAFRAME
    st.dataframe(
        df,
        column_config={
            "Crédito": st.column_config.NumberColumn(format="R$ %.2f"),
            "Entrada": st.column_config.NumberColumn(format="R$ %.2f"),
            "Custo Total": st.column_config.NumberColumn(format="R$ %.2f"),
            "Saldo Devedor": st.column_config.NumberColumn(format="R$ %.2f"),
            "Parcela": st.column_config.NumberColumn(format="R$ %.2f"),
            "Entrada (%)": st.column_config.NumberColumn(format="%.2f %%"),
            "Custo Real (%)": st.column_config.NumberColumn(format="%.2f %%"),
        }, hide_index=True, use_container_width=True
    )

    # EXCEL EXPORT (MANTENDO O VERDE PRO CLIENTE)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='JBS_PIFFER')
        wb = writer.book
        ws = writer.sheets['JBS_PIFFER']
        
        header_fmt = wb.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top',
            'fg_color': '#1f4e3d', 'font_color': '#FFFFFF', 'border': 1
        })
        money_fmt = wb.add_format({'num_format': 'R$ #,##0.00'})
        pct_fmt = wb.add_format({'num_format': '0.00%'})
        
        for col_num, value in enumerate(df.columns.values):
            ws.write(0, col_num, value, header_fmt)
            
        ws.set_column('A:A', 25) # Status
        ws.set_column('B:C', 15)
        ws.set_column('D:E', 18, money_fmt)
        ws.set_column('F:F', 12, pct_fmt)
        ws.set_column('G:G', 18, money_fmt)
        ws.set_column('H:H', 12, pct_fmt)
        ws.set_column('I:I', 18, money_fmt)
        ws.set_column('J:K', 12)

    st.download_button("📥 BAIXAR EXCEL JBS", buf.getvalue(), "JBS_Piffer_Selection.xlsx")

else:
    if not texto_site:
        st.info("Aguardando dados...")

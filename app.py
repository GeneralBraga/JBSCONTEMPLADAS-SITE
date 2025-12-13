
import streamlit as st
import pandas as pd
import re
import itertools
from io import BytesIO
from fpdf import FPDF
import os

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="001 JBS SNIPER DARK",
    page_icon="🎯",
    layout="wide"
)

# --- CORES (IDENTIDADE VISUAL DARK/GOLD) ---
COLOR_BG = "#0e1117"
COLOR_SIDEBAR = "#262730"
COLOR_GOLD = "#84754e"     # Dourado JBS
COLOR_TEXT = "#ecece4"     # Bege Claro

# --- CSS PERSONALIZADO ---
st.markdown(f"""
<style>
    .stApp {{background-color: {COLOR_BG}; color: {COLOR_TEXT};}}
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
        color: {COLOR_TEXT};
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }}
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div {{
        background-color: #1c1f26; 
        color: white; 
        border: 1px solid {COLOR_GOLD};
    }}
    div[data-testid="stDataFrame"], .streamlit-expanderHeader {{
        border: 1px solid {COLOR_GOLD};
        background-color: #1c1f26;
        color: {COLOR_GOLD};
    }}
    h1, h2, h3 {{color: {COLOR_GOLD} !important; font-family: 'Helvetica', sans-serif;}}
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
c1, c2 = st.columns([1, 5])
with c1:
    st.markdown(f"<h1 style='color:{COLOR_GOLD}; font-size: 50px;'>JBS</h1>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<h1 style='margin-top: 15px; margin-bottom: 0px;'>SISTEMA SNIPER V32</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0px; color: {COLOR_TEXT} !important;'>Modo Sanguesuga Dark - Motor Trator V32</h3>", unsafe_allow_html=True)

st.markdown(f"<hr style='border: 1px solid {COLOR_GOLD}; margin-top: 0;'>", unsafe_allow_html=True)

# --- FUNÇÕES ---
def limpar_moeda(texto):
    if not texto: return 0.0
    texto = str(texto).lower().replace('r$', '').replace('.', '').replace(',', '.').strip()
    try:
        # Busca o primeiro número válido na string
        nums = re.findall(r"[\d\.]+", texto)
        if nums: return float(nums[0])
        return 0.0
    except:
        return 0.0

def extrair_dados_universal(texto_bruto):
    # LÓGICA V32 (PIFFER SANGUESUGA) - A MAIS AGRESSIVA
    lista_cotas = []
    
    # 1. Normaliza
    texto = "\n".join([line.strip() for line in texto_bruto.splitlines() if line.strip()])
    
    # 2. Split inteligente (Keyword Strategy)
    # Tenta quebrar onde aparece "Crédito" ou padrões de admin
    blocos = re.split(r'(?i)(?=Crédito|Admin|Cód)', texto)
    if len(blocos) < 2: blocos = texto.split('\n\n') # Fallback

    id_cota = 1
    for bloco in blocos:
        if "R$" not in bloco and "r$" not in bloco.lower(): continue
        
        bloco_lower = bloco.lower()

        # --- EXTRAÇÃO DE VALORES (REGEX FLEXÍVEL) ---
        
        # Crédito
        match_cred = re.search(r'(?:crédito|valor|bem).*?r\$\s?([\d\.,]+)', bloco_lower)
        if match_cred: 
            credito = limpar_moeda(match_cred.group(1))
        else:
            # Tenta achar o maior valor se não tiver a palavra crédito
            valores = re.findall(r'r\$\s?([\d\.,]+)', bloco_lower)
            vals = sorted([limpar_moeda(v) for v in valores], reverse=True)
            credito = vals[0] if vals else 0

        # Entrada
        match_ent = re.search(r'(?:entrada|quero|ágio).*?r\$\s?([\d\.,]+)', bloco_lower)
        if match_ent: 
            entrada = limpar_moeda(match_ent.group(1))
        else:
            # Se não achou explícito, tenta pegar o segundo maior valor (arriscado mas funciona pra Piffer)
            valores = re.findall(r'r\$\s?([\d\.,]+)', bloco_lower)
            vals = sorted([limpar_moeda(v) for v in valores], reverse=True)
            entrada = vals[1] if len(vals) > 1 else 0

        # Parcela e Prazo (Motor V32)
        match_prz = re.search(r'(\d+)\s*[xX]\s*r?\$\s?([\d\.,]+)', bloco_lower)
        prazo = 0
        parcela = 0

        if match_prz:
            prazo = int(match_prz.group(1))
            parcela = limpar_moeda(match_prz.group(2))
        else:
            # Tenta isolados
            match_parc = re.search(r'(?:parcela|mensal).*?r\$\s?([\d\.,]+)', bloco_lower)
            if match_parc: parcela = limpar_moeda(match_parc.group(1))
            
            match_prazo = re.search(r'(?:prazo|meses).*?(\d+)', bloco_lower)
            if match_prazo: prazo = int(match_prazo.group(1))

        # Admin
        admins = ['BRADESCO', 'SANTANDER', 'ITAÚ', 'ITAU', 'PORTO', 'CAIXA', 'BANCO DO BRASIL', 'BB', 'RODOBENS', 'EMBRACON', 'ANCORA', 'MYCON', 'SICREDI', 'SICOOB', 'MAPFRE', 'HS', 'YAMAHA', 'ZEMA', 'BANCORBRÁS', 'SERVOPA', 'UNIFISA']
        admin_encontrada = "OUTROS"
        for adm in admins:
            if adm.lower() in bloco_lower:
                admin_encontrada = adm.upper()
                break
        
        if admin_encontrada == "OUTROS" and parcela == 0: continue # Lixo

        # Tipo
        tipo_bem = "Geral"
        if "imóvel" in bloco_lower or "imovel" in bloco_lower: tipo_bem = "Imóvel"
        elif "automóvel" in bloco_lower or "veículo" in bloco_lower: tipo_bem = "Automóvel"
        elif "caminhão" in bloco_lower: tipo_bem = "Pesados"

        # --- CÁLCULOS ---
        saldo_devedor = prazo * parcela
        if saldo_devedor == 0 and credito > 0: saldo_devedor = credito * 1.3 # Estimativa se não achar parcela
            
        custo_total = entrada + saldo_devedor
        
        if credito > 5000:
            lista_cotas.append({
                'ID': id_cota, 'Admin': admin_encontrada, 'Tipo': tipo_bem,
                'Crédito': credito, 'Entrada': entrada,
                'Parcela': parcela, 'Saldo': saldo_devedor, 'CustoTotal': custo_total,
                'EntradaPct': (entrada/credito) if credito else 0
            })
            id_cota += 1
            
    return lista_cotas

def processar_combinacoes(cotas, min_cred, max_cred, max_ent, max_parc, max_custo, tipo_filtro):
    combinacoes_validas = []
    cotas_por_admin = {}
    
    for cota in cotas:
        if tipo_filtro != "Todos" and cota['Tipo'] != tipo_filtro: continue
        adm = cota['Admin']
        if adm not in cotas_por_admin: cotas_por_admin[adm] = []
        cotas_por_admin[adm].append(cota)
    
    progress_bar = st.progress(0)
    total_admins = len(cotas_por_admin)
    current = 0

    if total_admins == 0: return pd.DataFrame()

    for admin, grupo in cotas_por_admin.items():
        if admin == "OUTROS": continue
        current += 1
        progress_bar.progress(int((current / total_admins) * 100))
        grupo.sort(key=lambda x: x['EntradaPct'])
        
        count = 0
        max_ops = 500000 
        
        # Combinações de 1 até 6
        for r in range(1, 7):
            iterator = itertools.combinations(grupo, r)
            while True:
                try:
                    combo = next(iterator)
                    count += 1
                    if count > max_ops: break
                    
                    soma_ent = sum(c['Entrada'] for c in combo)
                    if soma_ent > (max_ent * 1.05): continue
                    
                    soma_cred = sum(c['Crédito'] for c in combo)
                    if soma_cred < min_cred or soma_cred > max_cred: continue
                    
                    soma_parc = sum(c['Parcela'] for c in combo)
                    if soma_parc > (max_parc * 1.05): continue
                    
                    soma_custo = sum(c['CustoTotal'] for c in combo)
                    soma_saldo = sum(c['Saldo'] for c in combo)

                    custo_real = (soma_custo / soma_cred) - 1
                    if custo_real > max_custo: continue
                    
                    # Colunas Novas
                    perc_entrada = soma_ent / soma_cred if soma_cred > 0 else 0
                    
                    ids = " + ".join([str(c['ID']) for c in combo])
                    detalhes = " || ".join([f"[ID {c['ID']}] {c['Tipo']} Cr: {c['Crédito']:,.0f}" for c in combo])
                    tipo_final = combo[0]['Tipo']
                    
                    status = "⚠️ PADRÃO"
                    if custo_real <= 0.20: status = "💎 OURO"
                    elif custo_real <= 0.35: status = "🔥 IMPERDÍVEL"
                    elif custo_real <= 0.45: status = "✅ OPORTUNIDADE"
                    
                    combinacoes_validas.append({
                        'Admin': admin, 'Status': status, 'Tipo': tipo_final, 'IDs': ids,
                        'Crédito Total': soma_cred, 
                        'Entrada Total': soma_ent,
                        '% Entrada': perc_entrada,
                        'Saldo Devedor': soma_saldo, 
                        'Parcela Total': soma_parc, 
                        'Custo Total': soma_custo, 
                        'Custo Real (%)': custo_real * 100, 
                        'Detalhes': detalhes
                    })
                    if len([x for x in combinacoes_validas if x['Admin'] == admin]) > 100: break
                except StopIteration: break
            if count > max_ops: break
    progress_bar.empty()
    return pd.DataFrame(combinacoes_validas)

# --- PDF ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(132, 117, 78)
        self.rect(0, 0, 297, 22, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 6) 
        self.cell(0, 10, 'JBS SNIPER - RELATÓRIO DE OPORTUNIDADES', 0, 1, 'C')
        self.ln(8)

def limpar_emojis(texto):
    return texto.encode('latin-1', 'ignore').decode('latin-1').replace("?", "").strip()

def gerar_pdf_final(df):
    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", size=8) 
    pdf.set_fill_color(236, 236, 228)
    pdf.set_text_color(0)
    pdf.set_font("Arial", 'B', 8)
    
    headers = ["Admin", "Status", "Credito", "Entrada", "% Ent", "Custo Tot", "Parcela", "Custo Real"]
    w = [25, 30, 30, 30, 15, 30, 25, 20] 
    
    for i, h in enumerate(headers): pdf.cell(w[i], 10, h, 1, 0, 'C', True)
    pdf.ln()
    
    pdf.set_font("Arial", size=7)
    for index, row in df.iterrows():
        try:
            status_clean = limpar_emojis(row['Status'])
            pdf.cell(w[0], 8, str(row['Admin'])[:15], 1, 0, 'C')
            pdf.cell(w[1], 8, status_clean, 1, 0, 'C')
            pdf.cell(w[2], 8, f"{row['Crédito Total']:,.2f}", 1, 0, 'R')
            pdf.cell(w[3], 8, f"{row['Entrada Total']:,.2f}", 1, 0, 'R')
            pdf.cell(w[4], 8, f"{row['% Entrada']*100:.1f}%", 1, 0, 'C')
            pdf.cell(w[5], 8, f"{row['Custo Total']:,.2f}", 1, 0, 'R')
            pdf.cell(w[6], 8, f"{row['Parcela Total']:,.2f}", 1, 0, 'R')
            pdf.cell(w[7], 8, f"{row['Custo Real (%)']:.2f}%", 1, 1, 'C')
        except: pass
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- APP ---
if 'df_resultado' not in st.session_state: st.session_state.df_resultado = None

with st.expander("📋 DADOS DO SITE (Colar aqui)", expanded=True):
    texto_site = st.text_area("", height=100, key="input_texto", placeholder="Cole o texto aqui...")

st.subheader("Filtros JBS")
tipo_bem = st.selectbox("Tipo de Bem", ["Todos", "Imóvel", "Automóvel", "Pesados"])

c1, c2 = st.columns(2)
min_c = c1.number_input("Crédito Mín (R$)", 0.0, step=1000.0, value=60000.0, format="%.2f")
max_c = c1.number_input("Crédito Máx (R$)", 0.0, step=1000.0, value=710000.0, format="%.2f")
max_e = c2.number_input("Entrada Máx (R$)", 0.0, step=1000.0, value=200000.0, format="%.2f")
max_p = c2.number_input("Parcela Máx (R$)", 0.0, step=100.0, value=5000.0, format="%.2f")
max_k = st.slider("Custo Máx (%)", 0.0, 1.0, 0.57, 0.01)

if st.button("🔍 LOCALIZAR OPORTUNIDADES"):
    if texto_site:
        cotas = extrair_dados_universal(texto_site)
        if cotas:
            st.session_state.df_resultado = processar_combinacoes(cotas, min_c, max_c, max_e, max_p, max_k, tipo_bem)
        else:
            st.error("Nenhuma cota identificada. O motor V32 não encontrou padrões válidos.")
    else:
        st.error("Cole os dados.")

if st.session_state.df_resultado is not None:
    df_show = st.session_state.df_resultado
    if not df_show.empty:
        df_show = df_show.sort_values(by='Custo Real (%)')
        st.success(f"{len(df_show)} Oportunidades Encontradas!")
        
        st.dataframe(
            df_show,
            column_config={
                "Crédito Total": st.column_config.NumberColumn(format="R$ %.2f"),
                "Entrada Total": st.column_config.NumberColumn(format="R$ %.2f"),
                "% Entrada": st.column_config.NumberColumn(format="%.2f %%"),
                "Saldo Devedor": st.column_config.NumberColumn(format="R$ %.2f"),
                "Parcela Total": st.column_config.NumberColumn(format="R$ %.2f"),
                "Custo Total": st.column_config.NumberColumn(format="R$ %.2f"),
                "Custo Real (%)": st.column_config.NumberColumn(format="%.2f %%"),
            }, hide_index=True
        )
        
        c_pdf, c_xls = st.columns(2)
        try:
            pdf_bytes = gerar_pdf_final(df_show)
            c_pdf.download_button("📄 Baixar PDF", pdf_bytes, "JBS_Relatorio.pdf", "application/pdf")
        except: c_pdf.error("Erro PDF")

        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df_ex = df_show.copy()
            df_ex['Custo Real (%)'] = df_ex['Custo Real (%)'] / 100
            df_ex.to_excel(writer, index=False, sheet_name='JBS_SNIPER')
            wb = writer.book
            ws = writer.sheets['JBS_SNIPER']
            fmt_money = wb.add_format({'num_format': 'R$ #,##0.00'})
            fmt_perc = wb.add_format({'num_format': '0.00%'})
            header_fmt = wb.add_format({'bold': True, 'fg_color': '#84754e', 'font_color': 'white', 'border': 1})
            
            for col_num, value in enumerate(df_ex.columns.values):
                ws.write(0, col_num, value, header_fmt)

            ws.set_column('A:B', 15)
            ws.set_column('E:M', 18, fmt_money)
            ws.set_column('G:G', 12, fmt_perc)
            ws.set_column('K:K', 12, fmt_perc)

        c_xls.download_button("📊 Baixar Excel", buf.getvalue(), "JBS_Calculo.xlsx")
    else:
        st.warning("Nenhuma oportunidade encontrada com estes filtros.")

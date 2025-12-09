
import streamlit as st
import pandas as pd
import re
import itertools
from io import BytesIO
from fpdf import FPDF
from datetime import datetime
import os

# --- CONFIGURAÇÃO ---
favicon_path = "logo_pdf.png" if os.path.exists("logo_pdf.png") else "🏛️"
st.set_page_config(page_title="JBS SNIPER", page_icon=favicon_path, layout="wide")

# --- CORES ---
COLOR_GOLD = "#84754e"
COLOR_BEIGE = "#ecece4"
COLOR_BG = "#0e1117"

# --- CSS ---
st.markdown(f"""
<style>
    .stApp {{background-color: {COLOR_BG}; color: {COLOR_BEIGE};}}
    .stButton>button {{width: 100%; background-color: {COLOR_GOLD}; color: white; border: none; border-radius: 6px; font-weight: bold; text-transform: uppercase; padding: 12px; letter-spacing: 1px;}}
    .stButton>button:hover {{background-color: #6b5e3d; color: {COLOR_BEIGE}; box-shadow: 0 2px 5px rgba(0,0,0,0.2);}}
    h1, h2, h3 {{color: {COLOR_GOLD} !important; font-family: 'Helvetica', sans-serif;}}
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div {{background-color: #1c1f26; color: white; border: 1px solid {COLOR_GOLD};}}
    div[data-testid="stDataFrame"], .streamlit-expanderHeader {{border: 1px solid {COLOR_GOLD}; background-color: #1c1f26;}}
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
c1, c2 = st.columns([1, 5])
with c1:
    if os.path.exists("logo_app.png"): st.image("logo_app.png", width=220)
    else: st.markdown(f"<h1 style='color:{COLOR_GOLD}'>JBS</h1>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<h1 style='margin-top: 15px; margin-bottom: 0px;'>SISTEMA SNIPER</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0px; color: {COLOR_BEIGE} !important;'>Ferramenta Exclusiva da JBS Contempladas</h3>", unsafe_allow_html=True)
st.markdown(f"<hr style='border: 1px solid {COLOR_GOLD}; margin-top: 0;'>", unsafe_allow_html=True)

# --- FUNÇÕES ---
def limpar_moeda(texto):
    if not texto: return 0.0
    texto = str(texto).lower().strip().replace('\xa0', '').replace('&nbsp;', '')
    texto = re.sub(r'[^\d\.,]', '', texto)
    if not texto: return 0.0
    try:
        if ',' in texto and '.' in texto: return float(texto.replace('.', '').replace(',', '.'))
        elif ',' in texto: return float(texto.replace(',', '.'))
        elif '.' in texto:
             if len(texto.split('.')[1]) == 2: return float(texto)
             return float(texto.replace('.', ''))
        return float(texto)
    except: return 0.0

def extrair_dados_universal(texto_copiado, tipo_selecionado):
    lista_cotas = []
    # Limpa linhas vazias
    linhas = [line.strip() for line in texto_copiado.split('\n') if line.strip()]
    
    # === MODO 1: PIFFER (HORIZONTAL) ===
    # Procura linhas que contêm tudo: Admin + Crédito + Entrada + Parcela (X)
    admins_regex = r'(?i)(bradesco|santander|itaú|itau|porto|caixa|banco do brasil|bb|rodobens|embracon|ancora|âncora|mycon|sicredi|sicoob|mapfre|hs|yamaha|zema|bancorbrás|bancorbras|servopa|disal|volkswagen|chevrolet|toyota|bancorbras|cnp|magalu|serello|becker|colombo|spengler|unicoob)'
    
    for linha in linhas:
        # Regex Piffer: 169X R$ 400
        match_piffer = re.search(r'(\d{1,3})\s*[xX]\s*R?\$\s?([\d\.,]+)', linha)
        match_admin = re.search(admins_regex, linha)
        
        if match_piffer and match_admin and "R$" in linha:
            # É uma linha Piffer!
            valores = re.findall(r'R\$\s?([\d\.,]+)', linha)
            vals_float = sorted([limpar_moeda(v) for v in valores], reverse=True)
            
            # Remove o valor da parcela da lista de candidatos a Crédito/Entrada
            parc_val = limpar_moeda(match_piffer.group(2))
            vals_limpos = [v for v in vals_float if abs(v - parc_val) > 1.0]
            
            if len(vals_limpos) >= 2:
                credito = vals_limpos[0]
                entrada = vals_limpos[1]
                prazo = int(match_piffer.group(1))
                parcela = parc_val
                
                # Monta e salva direto
                saldo = prazo * parcela
                lista_cotas.append({
                    'ID': len(lista_cotas)+1, 'Admin': match_admin.group(0).upper(), 'Tipo': tipo_selecionado,
                    'Crédito': credito, 'Entrada': entrada, 'Parcela': parcela,
                    'Saldo': saldo, 'CustoTotal': entrada+saldo, 'Prazo': prazo,
                    'EntradaPct': (entrada/credito), 'Modo': 'Piffer'
                })

    # === MODO 2: TOP CONTEMPLADAS (VERTICAL / RÓTULOS) ===
    # Se o modo 1 pegou pouca coisa, ou para complementar, rodamos o modo vertical
    # Este modo lê linha a linha procurando rótulos
    
    cota_temp = {}
    
    for i, linha in enumerate(linhas):
        linha_lower = linha.lower()
        
        # 1. GATILHO ADMIN (Início de nova cota)
        match_admin = re.search(admins_regex, linha_lower)
        
        # Se achou admin e a linha é curta (pra não pegar texto aleatório)
        if match_admin and len(linha) < 50:
            # Salva a anterior se válida
            if cota_temp and cota_temp.get('Crédito', 0) > 0 and cota_temp.get('Entrada', 0) > 0:
                if cota_temp.get('Saldo', 0) == 0: # Fallback matemático
                     cota_temp['Saldo'] = max(0, (cota_temp['Crédito'] * 1.25) - cota_temp['Entrada'])
                     prazo_est = 80 if "Auto" in tipo_selecionado else 180
                     cota_temp['Parcela'] = cota_temp['Saldo'] / prazo_est
                     cota_temp['Prazo'] = prazo_est
                cota_temp['CustoTotal'] = cota_temp['Entrada'] + cota_temp['Saldo']
                cota_temp['EntradaPct'] = cota_temp['Entrada'] / cota_temp['Crédito']
                lista_cotas.append(cota_temp)

            # Nova Cota
            cota_temp = {
                'ID': len(lista_cotas)+1, 'Admin': match_admin.group(0).upper(), 'Tipo': tipo_selecionado,
                'Crédito': 0.0, 'Entrada': 0.0, 'Parcela': 0.0, 'Saldo': 0.0, 'Prazo': 0
            }
            
            # TOP CONTEMPLADAS: O crédito costuma vir na linha logo abaixo do nome
            if i+1 < len(linhas):
                prox = linhas[i+1]
                if "R$" in prox and "Entrada" not in prox:
                    cota_temp['Crédito'] = limpar_moeda(prox)

        # 2. CAPTURA ENTRADA (Rótulo "Entrada:")
        if "entrada:" in linha_lower and cota_temp:
            # Tenta pegar na mesma linha ou na próxima
            val = limpar_moeda(linha)
            if val == 0 and i+1 < len(linhas): val = limpar_moeda(linhas[i+1])
            if val > 0: cota_temp['Entrada'] = val

        # 3. CAPTURA PARCELA (Rótulo "Parcelas:")
        if ("parcela:" in linha_lower or "parcelas:" in linha_lower) and cota_temp:
            texto_alvo = linha
            if "x" not in linha_lower and i+1 < len(linhas): texto_alvo = linhas[i+1]
            
            # Regex Top: "31 x R$ 1.380,84"
            match_parc = re.search(r'(\d{1,3})\s*[xX]\s*R?\$\s?([\d\.,]+)', texto_alvo)
            if match_parc:
                cota_temp['Prazo'] = int(match_parc.group(1))
                cota_temp['Parcela'] = limpar_moeda(match_parc.group(2))
                cota_temp['Saldo'] = cota_temp['Prazo'] * cota_temp['Parcela']

    # Salva a última do buffer
    if cota_temp and cota_temp.get('Crédito', 0) > 0 and cota_temp.get('Entrada', 0) > 0:
        if cota_temp.get('Saldo', 0) == 0:
             cota_temp['Saldo'] = max(0, (cota_temp['Crédito'] * 1.25) - cota_temp['Entrada'])
             prazo_est = 80 if "Auto" in tipo_selecionado else 180
             cota_temp['Parcela'] = cota_temp['Saldo'] / prazo_est
             cota_temp['Prazo'] = prazo_est
        cota_temp['CustoTotal'] = cota_temp['Entrada'] + cota_temp['Saldo']
        cota_temp['EntradaPct'] = cota_temp['Entrada'] / cota_temp['Crédito']
        lista_cotas.append(cota_temp)

    # Remove duplicatas (caso o modo Piffer e Top tenham pego a mesma linha)
    # Filtra por ID único visual ou conteúdo
    
    return lista_cotas

def processar_combinacoes(cotas, min_cred, max_cred, max_ent, max_parc, max_custo, tipo_filtro, admin_filtro):
    combinacoes_validas = []
    cotas_por_admin = {}
    
    for cota in cotas:
        if admin_filtro != "Todas" and cota['Admin'] != admin_filtro: continue
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
        max_ops = 5000000 
        
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
                    
                    soma_saldo = sum(c['Saldo'] for c in combo)
                    custo_total_exibicao = soma_ent + soma_saldo
                    
                    prazo_medio = int(soma_saldo / soma_parc) if soma_parc > 0 else 0

                    custo_real = (custo_total_exibicao / soma_cred) - 1
                    if custo_real > max_custo: continue
                    
                    ids = " + ".join([str(c['ID']) for c in combo])
                    detalhes = " || ".join([f"[ID {c['ID']}] 💰 CR: R$ {c['Crédito']:,.0f}" for c in combo])
                    tipo_final = combo[0]['Tipo']
                    
                    status = "⚠️ PADRÃO"
                    if custo_real <= 0.20: status = "💎 OURO"
                    elif custo_real <= 0.35: status = "🔥 IMPERDÍVEL"
                    elif custo_real <= 0.45: status = "✨ EXCELENTE"
                    elif custo_real <= 0.50: status = "✅ OPORTUNIDADE"
                    
                    entrada_pct = (soma_ent / soma_cred)
                    
                    combinacoes_validas.append({
                        'STATUS': status, 'ADMINISTRADORA': admin, 'TIPO': tipo_final, 'IDS': ids,
                        'CRÉDITO TOTAL': soma_cred, 'ENTRADA TOTAL': soma_ent,
                        'ENTRADA %': entrada_pct * 100,
                        'SALDO DEVEDOR': soma_saldo,
                        'CUSTO TOTAL': custo_total_exibicao,
                        'PRAZO': prazo_medio,
                        'PARCELAS': soma_parc,
                        'CUSTO EFETIVO %': custo_real * 100,
                        'DETALHES': detalhes
                    })
                    if len([x for x in combinacoes_validas if x['ADMINISTRADORA'] == admin]) > 500: break
                except StopIteration: break
            if count > max_ops: break
    progress_bar.empty()
    return pd.DataFrame(combinacoes_validas)

# --- PDF ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(132, 117, 78)
        self.rect(0, 0, 297, 22, 'F')
        if os.path.exists("logo_pdf.png"): self.image('logo_pdf.png', 5, 3, 35)
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(45, 6) 
        self.cell(0, 10, 'RELATÓRIO SNIPER DE OPORTUNIDADES', 0, 1, 'L')
        self.ln(8)

def limpar_emojis(texto):
    return texto.encode('latin-1', 'ignore').decode('latin-1').replace("?", "").strip()

def gerar_pdf_final(df):
    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", size=7)
    pdf.set_fill_color(236, 236, 228)
    pdf.set_text_color(0)
    pdf.set_font("Arial", 'B', 7)
    headers = ["STS", "ADM", "TIPO", "CREDITO", "ENTRADA", "ENT%", "SALDO", "CUSTO TOT", "PRZ", "PARCELA", "EFET%", "DETALHES"]
    w = [20, 20, 12, 22, 22, 10, 22, 22, 8, 18, 10, 95] 
    for i, h in enumerate(headers): pdf.cell(w[i], 8, h, 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font("Arial", size=7)
    for index, row in df.iterrows():
        status_clean = limpar_emojis(row['STATUS'])
        pdf.cell(w[0], 8, status_clean, 1, 0, 'C')
        pdf.cell(w[1], 8, limpar_emojis(str(row['ADMINISTRADORA'])), 1, 0, 'C')
        pdf.cell(w[2], 8, limpar_emojis(str(row['TIPO'])), 1, 0, 'C')
        pdf.cell(w[3], 8, f"{row['CRÉDITO TOTAL']:,.0f}", 1, 0, 'R')
        pdf.cell(w[4], 8, f"{row['ENTRADA TOTAL']:,.0f}", 1, 0, 'R')
        pdf.cell(w[5], 8, f"{row['ENTRADA %']:.1f}%", 1, 0, 'C')
        pdf.cell(w[6], 8, f"{row['SALDO DEVEDOR']:,.0f}", 1, 0, 'R')
        pdf.cell(w[7], 8, f"{row['CUSTO TOTAL']:,.0f}", 1, 0, 'R')
        pdf.cell(w[8], 8, str(row['PRAZO']), 1, 0, 'C')
        pdf.cell(w[9], 8, f"{row['PARCELAS']:,.0f}", 1, 0, 'R')
        pdf.cell(w[10], 8, f"{row['CUSTO EFETIVO %']:.1f}%", 1, 0, 'C')
        detalhe = limpar_emojis(row['DETALHES'])
        pdf.cell(w[11], 8, detalhe[:75], 1, 1, 'L')
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- APP ---
if 'df_resultado' not in st.session_state: st.session_state.df_resultado = None

with st.expander("📋 DADOS DO SITE (Colar aqui)", expanded=True):
    texto_site = st.text_area("", height=100, key="input_texto")
    if texto_site:
        cotas_lidas = extrair_dados_universal(texto_site, "Geral")
        st.info(f"Leitura bruta: {len(cotas_lidas)} linhas identificadas.")
        admins_unicas = sorted(list(set([c['Admin'] for c in cotas_lidas])))
        st.session_state['admins_disponiveis'] = ["Todas"] + admins_unicas
        with st.expander("🕵️‍♂️ Ver o que o robô leu (Diagnóstico)"):
            if cotas_lidas: st.dataframe(pd.DataFrame(cotas_lidas)[['ID','Admin','Tipo','Crédito','Entrada','Parcela','Saldo','Prazo']])
    else:
        st.session_state['admins_disponiveis'] = ["Todas"]

st.subheader("Filtros JBS")
col_tipo, col_admin = st.columns(2)
tipo_bem = col_tipo.selectbox("Tipo de Bem", ["Todos", "Imóvel", "Automóvel", "Pesados"])
admin_filtro = col_admin.selectbox("Administradora", st.session_state['admins_disponiveis'])

c1, c2 = st.columns(2)
min_c = c1.number_input("Crédito Mín (R$)", 0.0, step=1000.0, value=60000.0, format="%.2f")
max_c = c1.number_input("Crédito Máx (R$)", 0.0, step=1000.0, value=710000.0, format="%.2f")
max_e = c2.number_input("Entrada Máx (R$)", 0.0, step=1000.0, value=200000.0, format="%.2f")
max_p = c2.number_input("Parcela Máx (R$)", 0.0, step=100.0, value=4500.0, format="%.2f")
max_k = st.slider("Custo Máx (%)", 0.0, 1.0, 0.55, 0.01)

if st.button("🔍 LOCALIZAR OPORTUNIDADES"):
    if texto_site:
        cotas = extrair_dados_universal(texto_site, tipo_bem)
        if cotas:
            st.session_state.df_resultado = processar_combinacoes(cotas, min_c, max_c, max_e, max_p, max_k, tipo_bem, admin_filtro)
        else:
            st.error("Nenhuma cota lida.")
    else:
        st.error("Cole os dados.")

if st.session_state.df_resultado is not None:
    df_show = st.session_state.df_resultado
    if not df_show.empty:
        df_show = df_show.sort_values(by='CUSTO EFETIVO %')
        st.success(f"{len(df_show)} Oportunidades Encontradas!")
        
        st.dataframe(
            df_show,
            column_config={
                "CRÉDITO TOTAL": st.column_config.NumberColumn(format="R$ %.2f"),
                "ENTRADA TOTAL": st.column_config.NumberColumn(format="R$ %.2f"),
                "ENTRADA %": st.column_config.NumberColumn(format="%.2f %%"),
                "SALDO DEVEDOR": st.column_config.NumberColumn(format="R$ %.2f"),
                "CUSTO TOTAL": st.column_config.NumberColumn(format="R$ %.2f"), 
                "PARCELAS": st.column_config.NumberColumn(format="R$ %.2f"),
                "CUSTO EFETIVO %": st.column_config.NumberColumn(format="%.2f %%"),
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
            df_ex['ENTRADA %'] = df_ex['ENTRADA %'] / 100
            df_ex['CUSTO EFETIVO %'] = df_ex['CUSTO EFETIVO %'] / 100
            df_ex.to_excel(writer, index=False, sheet_name='JBS')
            wb = writer.book
            ws = writer.sheets['JBS']
            header_fmt = wb.add_format({'bold': True, 'bg_color': '#ecece4', 'border': 1})
            fmt_money = wb.add_format({'num_format': 'R$ #,##0.00'})
            fmt_perc = wb.add_format({'num_format': '0.00%'})
            for col_num, value in enumerate(df_ex.columns.values): ws.write(0, col_num, value, header_fmt)
            ws.set_column('E:F', 18, fmt_money) 
            ws.set_column('G:G', 12, fmt_perc)  
            ws.set_column('H:I', 18, fmt_money) 
            ws.set_column('K:K', 15, fmt_money) 
            ws.set_column('L:L', 12, fmt_perc)  
            ws.set_column('M:M', 70)
            ws.set_column('A:D', 15)
        c_xls.download_button("📊 Baixar Excel", buf.getvalue(), "JBS_Calculo.xlsx")
    else:
        st.warning("Nenhuma oportunidade com estes filtros.")

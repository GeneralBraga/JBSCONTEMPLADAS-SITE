
import streamlit as st
import pandas as pd
import re
import itertools
from io import BytesIO

st.set_page_config(page_title="Sniper de Consórcio", page_icon="🎯", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        background-color: #0e1117;
        color: white;
        border: 1px solid #363b42;
    }
    .stButton>button:hover {
        border-color: #00ff00;
        color: #00ff00;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
def limpar_moeda(texto):
    if not texto: return 0.0
    texto = str(texto).lower().strip()
    texto = texto.replace('\xa0', '').replace('&nbsp;', '')
    texto = re.sub(r'[^\d\.,]', '', texto)
    if not texto: return 0.0
    try:
        if ',' in texto and '.' in texto: return float(texto.replace('.', '').replace(',', '.'))
        elif ',' in texto: return float(texto.replace(',', '.'))
        elif '.' in texto:
             partes = texto.split('.')
             if len(partes[-1]) == 2: return float(texto)
             return float(texto.replace('.', ''))
        return float(texto)
    except: return 0.0

def extrair_dados_universal(texto_copiado):
    lista_cotas = []
    texto_limpo = "\n".join([line.strip() for line in texto_copiado.split('\n') if line.strip()])
    
    # Tenta quebrar por palavras-chave de admin ou blocos
    blocos = re.split(r'(?i)(?=imóvel|imovel|automóvel|automovel|veículo)', texto_limpo)
    if len(blocos) < 2: blocos = texto_limpo.split('\n\n')

    id_cota = 1
    for bloco in blocos:
        if len(bloco) < 20: continue
        bloco_lower = bloco.lower()
        
        admins_conhecidas = ['BRADESCO', 'SANTANDER', 'ITAÚ', 'ITAU', 'PORTO', 'CAIXA', 'BANCO DO BRASIL', 'BB', 'RODOBENS', 'EMBRACON', 'ANCORA', 'ÂNCORA', 'MYCON', 'SICREDI', 'SICOOB', 'MAPFRE', 'HS', 'YAMAHA', 'ZEMA', 'BANCORBRÁS', 'BANCORBRAS', 'SERVOPA']
        admin_encontrada = "OUTROS"
        
        for adm in admins_conhecidas:
            if adm.lower() in bloco_lower:
                admin_encontrada = adm.upper()
                break
        
        if admin_encontrada == "OUTROS" and "r$" not in bloco_lower: continue

        credito = 0.0
        match_cred = re.search(r'(?:crédito|credito|bem|valor)[^\d\n]*?R\$\s?([\d\.,]+)', bloco_lower)
        if match_cred: credito = limpar_moeda(match_cred.group(1))
        else:
            valores = re.findall(r'R\$\s?([\d\.,]+)', bloco)
            vals_float = sorted([limpar_moeda(v) for v in valores], reverse=True)
            if vals_float: credito = vals_float[0]

        entrada = 0.0
        match_ent = re.search(r'(?:entrada|ágio|agio|quero|pago)[^\d\n]*?R\$\s?([\d\.,]+)', bloco_lower)
        if match_ent: entrada = limpar_moeda(match_ent.group(1))
        else:
            valores = re.findall(r'R\$\s?([\d\.,]+)', bloco)
            vals_float = sorted([limpar_moeda(v) for v in valores], reverse=True)
            if len(vals_float) > 1: entrada = vals_float[1]

        regex_parcelas = r'(\d+)\s*[xX]\s*R?\$\s?([\d\.,]+)'
        todas_parcelas = re.findall(regex_parcelas, bloco)
        
        saldo_devedor = 0.0
        parcela_teto = 0.0
        for prazo_str, valor_str in todas_parcelas:
            pz = int(prazo_str)
            vlr = limpar_moeda(valor_str)
            saldo_devedor += (pz * vlr)
            if pz > 1 and vlr > parcela_teto: parcela_teto = vlr
            elif len(todas_parcelas) == 1: parcela_teto = vlr

        if credito > 0 and entrada > 0:
            if saldo_devedor == 0: saldo_devedor = (credito * 1.3) - entrada
            custo_total = entrada + saldo_devedor
            if credito > 5000: 
                lista_cotas.append({
                    'ID': id_cota,
                    'Admin': admin_encontrada,
                    'Crédito': credito,
                    'Entrada': entrada,
                    'Parcela': parcela_teto,
                    'Saldo': saldo_devedor,
                    'CustoTotal': custo_total,
                    'EntradaPct': (entrada/credito) if credito else 0
                })
                id_cota += 1
    return lista_cotas

def processar_combinacoes(cotas, min_cred, max_cred, max_ent, max_parc, max_custo):
    combinacoes_validas = []
    cotas_por_admin = {}
    for cota in cotas:
        adm = cota['Admin']
        if adm not in cotas_por_admin: cotas_por_admin[adm] = []
        cotas_por_admin[adm].append(cota)
    
    progress_bar = st.progress(0)
    total_admins = len(cotas_por_admin)
    current_admin = 0

    for admin, grupo in cotas_por_admin.items():
        current_admin += 1
        progress_bar.progress(int((current_admin / total_admins) * 100))
        grupo.sort(key=lambda x: x['EntradaPct'])
        
        count = 0
        max_ops = 3000000 
        
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
                    custo_real = (soma_custo / soma_cred) - 1
                    if custo_real > max_custo: continue
                    
                    ids = " + ".join([str(c['ID']) for c in combo])
                    detalhes = " || ".join([f"[ID {c['ID']}] Cr: {c['Crédito']:,.0f} Ent: {c['Entrada']:,.0f}" for c in combo])
                    
                    status = "⚠️ ALTO"
                    if custo_real <= 0.20: status = "💎 LUCRO"
                    elif custo_real <= 0.40: status = "🔥 TOP"
                    elif custo_real <= 0.55: status = "✅ OK"
                    
                    combinacoes_validas.append({
                        'Admin': admin,
                        'Status': status,
                        'IDs': ids,
                        'Crédito Total': soma_credito,
                        'Entrada Total': soma_entrada,
                        'Parcela Total': soma_parcela,
                        'Custo Real (%)': custo_real,
                        'Detalhes': detalhes
                    })
                    
                    if len([x for x in combinacoes_validas if x['Admin'] == admin]) > 200: break
                except StopIteration:
                    break
            if count > max_ops: break
            
    progress_bar.empty()
    return pd.DataFrame(combinacoes_validas)

# --- APP ---
st.title("🎯 Sniper Mobile V23")

with st.expander("📋 Passo 1: Colar Dados do Site", expanded=True):
    texto_site = st.text_area("Cole aqui (CTRL+A do site)", height=150)
    
    if texto_site:
        cotas_lidas = extrair_dados_universal(texto_site)
        st.info(f"Leitura: {len(cotas_lidas)} cotas identificadas.")
        with st.expander("🕵️‍♂️ Ver o que o robô leu (Diagnóstico)"):
            if cotas_lidas: st.dataframe(pd.DataFrame(cotas_lidas)[['ID','Admin','Crédito','Entrada']])
            else: st.error("Nada lido. Verifique a cópia.")

st.subheader("⚙️ Filtros")
col1, col2 = st.columns(2)
with col1:
    min_c = st.number_input("Crédito Mín", value=640000, step=10000)
    max_c = st.number_input("Crédito Máx", value=710000, step=10000)
with col2:
    max_e = st.number_input("Entrada Máx", value=280000, step=5000)
    max_p = st.number_input("Parcela Máx", value=4500, step=100)
max_k = st.slider("Custo Máx (%)", 0.0, 1.0, 0.55, 0.01)

if st.button("🚀 Processar", type="primary"):
    if texto_site:
        cotas = extrair_dados_universal(texto_site)
        if len(cotas) > 0:
            df = processar_combinacoes(cotas, min_c, max_c, max_e, max_p, max_k)
            if not df.empty:
                st.success(f"{len(df)} combinações!")
                st.dataframe(df.sort_values(by='Custo Real (%)'), hide_index=True)
                
                buf = BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("📥 Excel", buf.getvalue(), "sniper.xlsx")
            else:
                st.warning("Sem combinações para estes filtros.")
    else:
        st.error("Cole os dados primeiro.")

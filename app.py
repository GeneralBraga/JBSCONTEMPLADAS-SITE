
import streamlit as st
import pandas as pd
import re
import io
import xlsxwriter
import os

# --- CONFIGURAÇÃO VISUAL (DARK/GOLD) ---
st.set_page_config(page_title="JBS SNIPER V36", layout="wide", page_icon="🎯")

COLOR_GOLD = "#84754e"
COLOR_BG = "#0e1117"
COLOR_INPUT = "#1c1f26"

st.markdown(f"""
<style>
    .stApp {{background-color: {COLOR_BG}; color: #ecece4;}}
    .stButton>button {{background-color: {COLOR_GOLD}; color: white; border-radius: 6px; height: 50px; font-weight: bold;}}
    .stTextArea textarea {{background-color: {COLOR_INPUT}; color: white; border: 1px solid {COLOR_GOLD};}}
    div[data-testid="stDataFrame"] {{border: 1px solid {COLOR_GOLD};}}
    h1, h3 {{color: {COLOR_GOLD} !important;}}
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
st.title("JBS SNIPER V36 🎯")
st.markdown("### Especialista em Dados Piffer (Texto Grudado + Múltiplas Parcelas)")
st.divider()

# --- INTELIGÊNCIA V36 ---
def limpar_moeda(texto):
    if not texto: return 0.0
    # Remove R$, pontos e espaços, troca vírgula por ponto
    texto_clean = str(texto).lower().replace('r$', '').replace('.', '').replace(',', '.').strip()
    try:
        # Pega apenas números e ponto
        return float(re.findall(r"[\d\.]+", texto_clean)[0])
    except:
        return 0.0

def classificar_status(custo_real):
    # Termômetro do Custo
    if custo_real <= 0.18: return "💎 LUCRO COM DESÁGIO"
    if custo_real <= 0.25: return "🔥 IMPERDÍVEL"
    if custo_real <= 0.35: return "✅ OPORTUNIDADE"
    return "⚠️ PADRÃO"

def extrair_piffer_v36(texto_bruto):
    lista_cotas = []
    # 1. Pré-processamento: "Desgrudar" Admin do Valor (Ex: ITAÚR$ -> ITAÚ R$)
    texto_limpo = re.sub(r'([a-zA-ZÁ-Zr])(R\$)', r'\1 \2', texto_bruto)
    
    linhas = [line.strip() for line in texto_limpo.splitlines() if line.strip()]
    
    for linha in linhas:
        linha_lower = linha.lower()
        # Filtro básico: tem que ter R$ e algum número de parcelas (x) ou ser linha de destaque
        if "r$" not in linha_lower: continue

        # --- A. ADMINISTRADORA ---
        admins = ['BRADESCO', 'SANTANDER', 'ITAÚ', 'ITAU', 'PORTO', 'CAIXA', 'BANCO DO BRASIL', 'BB', 'RODOBENS', 'EMBRACON', 'ANCORA', 'MYCON', 'SICREDI', 'SICOOB', 'MAPFRE', 'HS', 'YAMAHA', 'ZEMA', 'BANCORBRÁS', 'SERVOPA', 'UNIFISA', 'REPASSE']
        admin_encontrada = "OUTROS"
        for adm in admins:
            if adm.lower() in linha_lower:
                admin_encontrada = adm.upper()
                break
        
        # --- B. CAPTURA DE VALORES (CRÉDITO E ENTRADA) ---
        # Regex que pega todos os valores monetários da linha
        valores_raw = re.findall(r'r\$\s?([\d\.,]+)', linha_lower)
        valores_float = sorted([limpar_moeda(v) for v in valores_raw], reverse=True)
        
        if len(valores_float) < 2: continue # Precisa pelo menos Credito e Entrada
        
        # Lógica: Maior valor = Crédito. Segundo Maior = Entrada.
        credito = valores_float[0]
        
        # --- C. PARCELAS E SALDO DEVEDOR (A MÁGICA DA SOMA) ---
        # Procura por padrões "Nx R$ Y" (Ex: 188x R$ 486,64)
        # O regex captura (N, Valor)
        padrao_parcelas = re.findall(r'(\d+)\s*[xX]\s*r?\$\s?([\d\.,]+)', linha_lower)
        
        saldo_devedor_real = 0.0
        parcela_display = 0.0
        prazo_display = 0
        maior_prazo = 0
        
        if padrao_parcelas:
            for pz_str, vlr_str in padrao_parcelas:
                p = int(pz_str)
                v = limpar_moeda(vlr_str)
                # Soma tudo para o Saldo Devedor (regra da Junção)
                saldo_devedor_real += (p * v)
                
                # Para exibir na coluna "Parcela" e "Prazo", pegamos a de maior prazo (parcela principal)
                if p > maior_prazo:
                    maior_prazo = p
                    prazo_display = p
                    parcela_display = v
        else:
            # Se não achou padrão Nx, tenta estimar saldo (fallback)
            continue

        # Correção da Entrada: As vezes a entrada é confundida com o valor da parcela.
        # Removemos valores próximos à parcela da lista de candidatos à entrada
        candidatos_entrada = [x for x in valores_float if x != credito and abs(x - parcela_display) > 5]
        entrada = candidatos_entrada[0] if candidatos_entrada else 0.0

        # --- D. CÁLCULOS FINAIS ---
        custo_total = saldo_devedor_real + entrada
        
        if credito > 0:
            custo_real_pct = (custo_total / credito) - 1
            entrada_pct = entrada / credito
        else:
            custo_real_pct = 0
            entrada_pct = 0
            
        status = classificar_status(custo_real_pct)
        detalhes = linha[:100] + "..." # Snippet da linha original

        lista_cotas.append({
            'Status': status,
            'Administradora': admin_encontrada,
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

# --- APP ---
with st.expander("📋 COLE OS DADOS AQUI (V36)", expanded=True):
    texto_input = st.text_area("", height=200, placeholder="Cole os dados da Piffer aqui...")

if texto_input:
    df = extrair_piffer_v36(texto_input)
    
    if not df.empty:
        # ORDENAÇÃO POR % CUSTO (Menor para Maior)
        df = df.sort_values(by='% Custo', ascending=True)
        
        st.success(f"✅ {len(df)} Oportunidades Processadas!")
        
        # PREVIEW
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
            },
            hide_index=True,
            use_container_width=True
        )
        
        # EXCEL DOWNLOAD
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='SNIPER_V36')
            wb = writer.book
            ws = writer.sheets['SNIPER_V36']
            
            # Formatos
            fmt_header = wb.add_format({'bold': True, 'bg_color': '#1f4e3d', 'font_color': 'white', 'border': 1})
            fmt_money = wb.add_format({'num_format': 'R$ #,##0.00'})
            fmt_pct = wb.add_format({'num_format': '0.00%'})
            
            # Aplicar Cabeçalho
            for col_num, value in enumerate(df.columns.values):
                ws.write(0, col_num, value, fmt_header)
            
            # Aplicar Colunas
            ws.set_column('A:B', 20) # Status / Admin
            ws.set_column('C:D', 18, fmt_money) # Cred / Ent
            ws.set_column('E:E', 12, fmt_pct) # % Ent
            ws.set_column('F:F', 10) # Prazo
            ws.set_column('G:I', 18, fmt_money) # Parc / Saldo / Custo
            ws.set_column('J:J', 12, fmt_pct) # % Custo
            ws.set_column('K:K', 50) # Detalhes

        st.download_button(
            label="📥 BAIXAR PLANILHA COMPLETA",
            data=buffer.getvalue(),
            file_name="Sniper_Piffer_V36.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.warning("Não consegui ler os dados. Verifique se copiou o texto corretamente.")

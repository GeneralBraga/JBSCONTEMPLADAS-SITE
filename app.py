
import streamlit as st
import pandas as pd
import re
import io
import xlsxwriter
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="001 JBS CONTEMPLADAS SNIPER", layout="wide", page_icon="🎯")

# --- ESTILOS CSS (Padrão Piffer/Verde) ---
COLOR_HEADER = "#1f4e3d" # Verde Escuro
COLOR_TEXT = "#ffffff"

st.markdown(f"""
<style>
    .stApp {{background-color: #f0f2f6;}}
    h1 {{color: {COLOR_HEADER}; font-family: 'Arial Black', sans-serif;}}
    div[data-testid="stDataFrame"] {{border: 2px solid {COLOR_HEADER};}}
    .stButton>button {{
        background-color: {COLOR_HEADER};
        color: white;
        font-weight: bold;
        border-radius: 5px;
        height: 50px;
    }}
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
st.markdown(f"# 🎯 001 JBS CONTEMPLADAS SNIPER")
st.markdown("**Modo Sanguesuga Completo**: Copie (Ctrl+A) o site e cole abaixo. O sistema recalcula tudo.")
st.divider()

# --- FUNÇÕES ---
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

        # 1. CRÉDITO
        match_cred = re.search(r'(?:crédito|valor).*?r\$\s?([\d\.,]+)', bloco_lower)
        if not match_cred: continue
        credito = limpar_moeda(match_cred.group(1))

        # 2. ENTRADA
        match_ent = re.search(r'(?:entrada|quero).*?r\$\s?([\d\.,]+)', bloco_lower)
        if not match_ent: continue 
        entrada = limpar_moeda(match_ent.group(1))

        # 3. PRAZO E PARCELA
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

        # 4. ADMIN E TIPO
        admins = ['BRADESCO', 'SANTANDER', 'ITAÚ', 'ITAU', 'PORTO', 'CAIXA', 'BANCO DO BRASIL', 'BB', 'RODOBENS', 'EMBRACON', 'ANCORA', 'MYCON', 'SICREDI', 'SICOOB', 'MAPFRE', 'HS', 'YAMAHA', 'ZEMA', 'BANCORBRÁS', 'SERVOPA', 'UNIFISA']
        admin_encontrada = "DIVERSOS"
        for adm in admins:
            if adm.lower() in bloco_lower:
                admin_encontrada = adm.upper()
                break

        tipo_bem = "Outros"
        if "imóvel" in bloco_lower or "imovel" in bloco_lower: tipo_bem = "Imóvel"
        elif "automóvel" in bloco_lower or "veículo" in bloco_lower or "carro" in bloco_lower: tipo_bem = "Automóvel"
        elif "caminhão" in bloco_lower or "pesado" in bloco_lower: tipo_bem = "Pesados"

        # --- CÁLCULOS MATEMÁTICOS ---
        saldo_devedor_calc = prazo * parcela
        custo_total_calc = saldo_devedor_calc + entrada # COLUNA NOVA PEDIDA
        
        if credito > 0:
            custo_real_pct = (custo_total_calc / credito) - 1
            entrada_pct = entrada / credito # COLUNA NOVA PEDIDA
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
            '% Entrada': entrada_pct,     # COLUNA SOLICITADA
            'Custo Total': custo_total_calc, # COLUNA SOLICITADA
            'Saldo Devedor': saldo_devedor_calc,
            'Parcela': parcela,
            'Custo Real (%)': custo_real_pct,
            'Prazo': prazo
        })

    return pd.DataFrame(lista_cotas)

# --- INTERFACE ---
with st.expander("📋 COLE O SITE INTEIRO AQUI (CTRL+A / CTRL+V)", expanded=True):
    texto_input = st.text_area("", height=150, placeholder="Cole aqui o conteúdo copiado do site...")

if texto_input:
    df = extrair_piffer_sanguesuga(texto_input)

    if not df.empty:
        df = df.sort_values(by=['Custo Real (%)'], ascending=True)

        st.success(f"🔍 {len(df)} Oportunidades - 001 JBS SNIPER")

        st.dataframe(
            df,
            column_config={
                "Crédito": st.column_config.NumberColumn(format="R$ %.2f"),
                "Entrada": st.column_config.NumberColumn(format="R$ %.2f"),
                "% Entrada": st.column_config.NumberColumn(format="%.2f %%"),
                "Custo Total": st.column_config.NumberColumn(format="R$ %.2f"),
                "Saldo Devedor": st.column_config.NumberColumn(format="R$ %.2f"),
                "Parcela": st.column_config.NumberColumn(format="R$ %.2f"),
                "Custo Real (%)": st.column_config.NumberColumn(format="%.2f %%"),
                "Status": st.column_config.TextColumn(width="medium"),
            },
            hide_index=True,
            use_container_width=True
        )

        # --- EXCEL ---
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='JBS_SNIPER')
            workbook = writer.book
            worksheet = writer.sheets['JBS_SNIPER']

            header_fmt = workbook.add_format({
                'bold': True, 'text_wrap': True, 'valign': 'top',
                'fg_color': '#1f4e3d', 'font_color': '#FFFFFF', 'border': 1
            })
            money_fmt = workbook.add_format({'num_format': 'R$ #,##0.00'})
            pct_fmt = workbook.add_format({'num_format': '0.00%'})

            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_fmt)

            # Ajuste Colunas
            worksheet.set_column('A:A', 25) # Status
            worksheet.set_column('B:C', 15) # Admin/Tipo
            worksheet.set_column('D:E', 18, money_fmt) 
            worksheet.set_column('F:F', 12, pct_fmt)   # % Entrada
            worksheet.set_column('G:G', 18, money_fmt) # Custo Total
            worksheet.set_column('H:H', 18, money_fmt) # Saldo
            worksheet.set_column('I:I', 15, money_fmt) # Parcela
            worksheet.set_column('J:J', 12, pct_fmt)   # Custo Real

        st.download_button(
            label="📥 BAIXAR EXCEL COMPLETO",
            data=buffer.getvalue(),
            file_name=f"001_JBS_{datetime.now().strftime('%d-%m')}.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.warning("Nenhuma cota identificada. Verifique o texto copiado.")

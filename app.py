
import streamlit as st
import pandas as pd
import re
import io
import xlsxwriter
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="SNIPER JBS - PIFFER", layout="wide", page_icon="🎯")

# --- ESTILOS CSS (Igual ao Print) ---
COLOR_HEADER = "#1f4e3d" # Verde Escuro Excel
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
st.markdown(f"# 🎯 SNIPER JBS - PIFFER")
st.markdown("**Modo Sanguesuga Completo**: Copie (Ctrl+A) o site da Piffer e cole abaixo. O sistema recalcula tudo.")
st.divider()

# --- FUNÇÕES DE LIMPEZA E CÁLCULO ---
def limpar_moeda(texto):
    if not texto: return 0.0
    texto = str(texto).lower().replace('r$', '').replace('.', '').replace(',', '.').strip()
    try:
        return float(re.findall(r"[\d\.]+", texto)[0])
    except:
        return 0.0

def classificar_status(custo_real):
    # Lógica baseada no Print enviado
    if custo_real <= 0.18: return "💎 LUCRO COM DESÁGIO"
    if custo_real <= 0.26: return "🔥 IMPERDÍVEL"
    if custo_real <= 0.35: return "✅ OPORTUNIDADE"
    return "⚠️ PADRÃO"

def extrair_piffer_sanguesuga(texto_bruto):
    lista_cotas = []
    
    # 1. Normalização do texto para facilitar Regex
    # Substitui quebras múltiplas por um marcador único e remove espaços extras
    texto = "\n".join([line.strip() for line in texto_bruto.splitlines() if line.strip()])
    
    # A Piffer costuma ter blocos que começam com "Cód" ou Nome do Banco
    # Vamos usar um split inteligente pelos blocos de cotas
    # Regex para encontrar blocos que contêm Crédito e Entrada próximos
    
    # Estratégia Sanguesuga: Achar padrões de "Crédito: R$ X" e varrer o entorno
    regex_bloco = r"(?i)(admin.*?|cód.*?)(?=admin|cód|$)" 
    # Como o copy paste pode variar, vamos iterar por padrões de valores
    
    # Padrão mais robusto: Divide o texto onde encontrar "Crédito" antecedido por quebras
    blocos = re.split(r'(?i)(?=Crédito)', texto)

    for bloco in blocos:
        if "R$" not in bloco: continue
        
        bloco_lower = bloco.lower()
        
        # --- EXTRAÇÃO DE VALORES ---
        
        # 1. CRÉDITO
        match_cred = re.search(r'(?:crédito|valor).*?r\$\s?([\d\.,]+)', bloco_lower)
        if not match_cred: continue
        credito = limpar_moeda(match_cred.group(1))
        
        # 2. ENTRADA
        match_ent = re.search(r'(?:entrada|quero).*?r\$\s?([\d\.,]+)', bloco_lower)
        if not match_ent: continue # Sem entrada não serve
        entrada = limpar_moeda(match_ent.group(1))
        
        # 3. PRAZO E PARCELA (CRUCIAL: REGRA MATEMÁTICA DO USUÁRIO)
        # Procura padrões como "50x R$ 1.000,00" ou "50 x 1000"
        # Pega a primeira ocorrência válida (geralmente a atual)
        match_prz = re.search(r'(\d+)\s*[xX]\s*r?\$\s?([\d\.,]+)', bloco_lower)
        
        prazo = 0
        parcela = 0
        
        if match_prz:
            prazo = int(match_prz.group(1))
            parcela = limpar_moeda(match_prz.group(2))
        else:
            # Tenta achar parcela isolada se não tiver o "X"
            match_parc = re.search(r'(?:parcela|mensal).*?r\$\s?([\d\.,]+)', bloco_lower)
            match_praz = re.search(r'(?:prazo|meses).*?(\d+)', bloco_lower)
            if match_parc and match_praz:
                parcela = limpar_moeda(match_parc.group(1))
                prazo = int(match_praz.group(1))
            else:
                continue # Se não achou prazo/parcela, pula, pois não dá pra calcular saldo
        
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

        # --- CÁLCULOS MATEMÁTICOS FORÇADOS ---
        # REGRA 1: SALDO DEVEDOR = PRAZO X PARCELA
        saldo_devedor_calc = prazo * parcela
        
        # REGRA 2: CUSTO TOTAL = SALDO DEVEDOR + ENTRADA
        custo_total_calc = saldo_devedor_calc + entrada
        
        # REGRA 3: CUSTO REAL (%)
        if credito > 0:
            custo_real_pct = (custo_total_calc / credito) - 1
            entrada_pct = entrada / credito
        else:
            custo_real_pct = 0
            entrada_pct = 0
            
        status = classificar_status(custo_real_pct)

        # Monta dicionário exatamente com as colunas do Print
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
with st.expander("📋 COLE O SITE INTEIRO AQUI (CTRL+A / CTRL+V)", expanded=True):
    texto_input = st.text_area("", height=150, placeholder="Cole aqui o conteúdo copiado do site...")

if texto_input:
    df = extrair_piffer_sanguesuga(texto_input)
    
    if not df.empty:
        # Ordenação inteligente: Primeiro Status, depois menor Custo Real
        df = df.sort_values(by=['Custo Real (%)'], ascending=True)
        
        st.success(f"🔍 {len(df)} Oportunidades Extraídas com Sucesso!")
        
        # FORMATAÇÃO VISUAL NA TELA
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
                "Status": st.column_config.TextColumn(width="medium"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        # --- BOTÃO DOWNLOAD EXCEL (ESTILO PRINT) ---
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='SNIPER_JBS')
            workbook = writer.book
            worksheet = writer.sheets['SNIPER_JBS']
            
            # Formatos
            header_fmt = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#1f4e3d', # Verde Escuro do Print
                'font_color': '#FFFFFF',
                'border': 1
            })
            money_fmt = workbook.add_format({'num_format': 'R$ #,##0.00'})
            pct_fmt = workbook.add_format({'num_format': '0.00%'})
            
            # Aplica Cabeçalho
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_fmt)
            
            # Aplica Formatação nas Colunas
            worksheet.set_column('A:A', 25) # Status
            worksheet.set_column('B:C', 15) # Admin/Tipo
            worksheet.set_column('D:E', 18, money_fmt) # Cred/Entrada
            worksheet.set_column('F:F', 12, pct_fmt) # Ent%
            worksheet.set_column('G:G', 18, money_fmt) # Custo Total
            worksheet.set_column('H:H', 12, pct_fmt) # Custo Real
            worksheet.set_column('I:I', 18, money_fmt) # Saldo
            worksheet.set_column('J:K', 12) # Prazo/Parcela

        st.download_button(
            label="📥 BAIXAR PLANILHA (FORMATO EXCEL VERDE)",
            data=buffer.getvalue(),
            file_name=f"Sniper_Piffer_{datetime.now().strftime('%d-%m')}.xlsx",
            mime="application/vnd.ms-excel"
        )
        
    else:
        st.warning("Nenhuma cota identificada. Certifique-se de copiar o texto contendo 'Crédito', 'Entrada' e 'X parcelas'.")

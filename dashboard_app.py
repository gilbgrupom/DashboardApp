import streamlit as st
import pandas as pd
import plotly.express as px
import io
import os
import signal
import sys
from streamlit.web import cli as stcli

# Tenta importar o pyautogui de forma segura para não quebrar na nuvem
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ModuleNotFoundError:
    PYAUTOGUI_AVAILABLE = False
    
# --- Função para localizar recursos internos do PyInstaller ---
def resource_path(relative_path):
    """ Retorna o caminho absoluto para o recurso, funcionando no desenvolvimento e no .exe """
    try:
        # O PyInstaller cria uma pasta temporária e guarda o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Configuração da Página ---
st.set_page_config(
    page_title="Dashboard de Análise de Dados",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # Obtém o PID do processo Streamlit atual.
    current_streamlit_pid = os.getpid() 

    col1, col2 = st.columns([1, 6])

    # Coluna da imagem (Logo)
    with col1:
        caminho_logo = resource_path("Logo_Pequena_Cinza.png")
        st.image(caminho_logo, width=160)

    # Coluna do título
    with col2:
        st.title("Dashboard Simples de Análise de Dados 📊")

        
    st.header("1. Upload e Configuração do Arquivo")

    # Componente de Upload de Arquivo 
    uploaded_file = st.file_uploader("Escolha um arquivo CSV ou TXT", type=["csv", "txt"])

    if uploaded_file is not None:
        
        # --- Configurações na Barra Lateral (Sidebar)  ---
        st.sidebar.header("Configurações de Leitura")
        encoding = st.sidebar.selectbox(
            "Selecione a Codificação:",
            options=["utf-8", "latin-1", "cp1252", "utf-16", "ascii", "utf-8-sig", "ISO-8859-1"],
            index=0
        )
        delimiter_input = st.sidebar.text_input(
            "Digite o Delimitador:",
            value='\t'
        )
        
        # Lógica de Tratamento do Delimitador 
        delimiter = delimiter_input
        if delimiter_input == "\\t":
            delimiter = "\t" 
        elif delimiter_input.strip() == "":
            delimiter = None 
            
        # --- Botão de Encerramento  ---
        st.sidebar.markdown("---")
        if st.sidebar.button("🔴 Encerrar Aplicativo"):
            pid_to_kill = current_streamlit_pid 
            st.sidebar.warning(f"Streamlit App iniciado com PID: {pid_to_kill}")
            
            if pid_to_kill:
                try:
                    pyautogui.hotkey('ctrl', 'w')
                    print(f"Encerrando pid: {pid_to_kill}")
                    os.kill(pid_to_kill, signal.SIGTERM)
                    st.warning(f"O aplicativo está sendo encerrado.")
                    st.stop() 
                except Exception as e:
                    st.sidebar.error(f"Erro ao encerrar o aplicativo: {e}")
            
        try:
            # --- 1.1. Leitura do Arquivo  ---
            uploaded_file.seek(0) 
            data = pd.read_csv(
                uploaded_file,
                encoding=encoding,
                sep=delimiter, 
                engine='python' 
            )
            
            st.success(f"Arquivo carregado com sucesso! Codificação: **{encoding}**")
            
            # --- 1.5. Pré-processamento: Latitude/Longitude  ---
            col_com_separador = None
            for col in data.columns:
                if data[col].astype(str).str.contains('\*').any():
                    col_com_separador = col
                    break
            
            if col_com_separador:
                st.info(f"📍 Coordenadas encontradas em **'{col_com_separador}'**.")
                try:
                    data[['latitude_processada', 'longitude_processada']] = data[col_com_separador].astype(str).str.split('\*', expand=True)
                    data['latitude_processada'] = pd.to_numeric(data['latitude_processada'], errors='coerce')
                    data['longitude_processada'] = pd.to_numeric(data['longitude_processada'], errors='coerce')
                    data.dropna(subset=['latitude_processada', 'longitude_processada'], inplace=True)
                    st.success("✅ Coordenadas processadas!")
                except Exception as e:
                    st.warning(f"Erro ao processar coordenadas: {e}")

            # ----------------------------------------------------------------------------------
            # MAPEAMENTO DE COLUNAS AGRUPADAS (MÚLTIPLA ESCOLHA)
            # ----------------------------------------------------------------------------------
            raw_cols = []
            for col in data.columns:
                base_name = col.split('.')[0] if '.' in col and col.split('.')[-1].isdigit() else col
                raw_cols.append(base_name)
            
            unique_display_cols = sorted(list(set(raw_cols)))

            st.dataframe(data.head()) 

            # ----------------------------------------------------------------------------------
            # SEÇÃO DE FILTROS AVANÇADOS
            # ----------------------------------------------------------------------------------
            st.header("2. Filtro de Dados (Opcional)")
            
            df_filtered = data.copy()

            col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
            
            with col_f1:
                filter_col = st.selectbox(
                    "Coluna para Filtrar:",
                    options=["-- Nenhum Filtro --"] + unique_display_cols,
                    index=0
                )
            
            if filter_col != "-- Nenhum Filtro --":
                target_cols = [c for c in data.columns if c == filter_col or c.startswith(f"{filter_col}.")]
                
                if len(target_cols) == 1:
                    col_type = df_filtered[filter_col].dtype
                    if pd.api.types.is_numeric_dtype(col_type):
                        with col_f2: op = st.selectbox("Operação:", ["Igual", "Menor que", "Maior que", "Entre"])
                        with col_f3:
                            if op == "Entre":
                                min_val, max_val = float(df_filtered[filter_col].min()), float(df_filtered[filter_col].max())
                                val_range = st.slider("Intervalo:", min_val, max_val, (min_val, max_val))
                                df_filtered = df_filtered[(df_filtered[filter_col] >= val_range[0]) & (df_filtered[filter_col] <= val_range[1])]
                            else:
                                val = st.number_input("Valor:", value=float(df_filtered[filter_col].median()))
                                if op == "Igual": df_filtered = df_filtered[df_filtered[filter_col] == val]
                                elif op == "Menor que": df_filtered = df_filtered[df_filtered[filter_col] < val]
                                elif op == "Maior que": df_filtered = df_filtered[df_filtered[filter_col] > val]
                    elif df_filtered[filter_col].nunique() < 20:
                        with col_f2: op = st.selectbox("Operação:", ["Igual", "Diferente"])
                        with col_f3:
                            unique_vals = sorted(df_filtered[filter_col].dropna().unique().tolist())
                            val = st.selectbox("Selecione o Valor:", options=unique_vals)
                            df_filtered = df_filtered[df_filtered[filter_col] == val] if op == "Igual" else df_filtered[df_filtered[filter_col] != val]
                    else:
                        with col_f2: st.info("Busca por texto")
                        with col_f3:
                            search_term = st.text_input("Digite o termo (Contém):")
                            if search_term: df_filtered = df_filtered[df_filtered[filter_col].astype(str).str.contains(search_term, case=False, na=False)]
                
                else:
                    with col_f2:
                        op = st.selectbox("Operação para Múltiplas:", ["Contém a opção", "Não contém a opção"])
                    with col_f3:
                        unique_vals = pd.unique(df_filtered[target_cols].values.ravel())
                        unique_vals = sorted([str(x) for x in unique_vals if pd.notna(x)])
                        val = st.selectbox("Selecione a Opção de Rejeição:", options=unique_vals)
                        
                        condition = df_filtered[target_cols].isin([val]).any(axis=1)
                        df_filtered = df_filtered[condition] if op == "Contém a opção" else df_filtered[~condition]

                st.info(f"Total de registros após filtro: **{len(df_filtered)}**")
            else:
                st.info(f"Nenhum filtro aplicado. Total: **{len(df_filtered)}**")

            data_to_plot = df_filtered 
            
            # ----------------------------------------------------------------------------------
            # Configuração da Visualização 
            # ----------------------------------------------------------------------------------
            st.header("3. Configuração da Visualização") 

            col1, col2, col3 = st.columns(3)
            with col1:
                chart_type = st.selectbox("Tipo de Gráfico:", options=["Barra", "Linha", "Pizza", "Mapa"])
            
            selected_variable_x = None
            selected_variable_y = None
            selected_group_col = None
            selected_variable_lat = None
            selected_variable_lon = None

            if chart_type == "Barra":
                with col2: selected_variable_x = st.selectbox("Eixo X:", options=unique_display_cols)
                with col3: selected_group_col = st.selectbox("Série (Cor):", options=["-- Nenhum --"] + [c for c in unique_display_cols if c != selected_variable_x])
                
            elif chart_type == "Pizza":
                with col2: selected_variable_x = st.selectbox("Categorias:", options=unique_display_cols)
                
            elif chart_type == "Mapa": 
                lat_options = [c for c in data_to_plot.columns if 'LAT' in c.upper() or 'PROCESSADA' in c.upper()]
                lon_options = [c for c in data_to_plot.columns if 'LON' in c.upper() or 'PROCESSADA' in c.upper()]
                with col2: selected_variable_lat = st.selectbox("Latitude:", options=lat_options if lat_options else data_to_plot.columns.tolist())
                with col3: selected_variable_lon = st.selectbox("Longitude:", options=lon_options if lon_options else data_to_plot.columns.tolist())
            
            else: # Linha
                with col2: selected_variable_x = st.selectbox("Eixo X:", options=unique_display_cols)
                with col3:
                    numeric_cols = [col for col in data_to_plot.columns if pd.api.types.is_numeric_dtype(data_to_plot[col])]
                    options_y = ["Contagem"] + numeric_cols
                    selected_variable_y = st.selectbox("Eixo Y:", options=options_y)
            
            # --- Renderização do Gráfico ---
            st.header("4. Visualização") 

            # FUNÇÃO DE PREPARAÇÃO BLINDADA CONTRA CONFLITOS DE NOMES DO PANDAS
            def preparar_dados_plot(df, col_x, col_group=None):
                cols_x_reais = [c for c in df.columns if c == col_x or c.startswith(f"{col_x}.")]
                
                if col_group and col_group != "-- Nenhum --":
                    cols_g_reais = [c for c in df.columns if c == col_group or c.startswith(f"{col_group}.")]
                    
                    if len(cols_x_reais) == 1 and len(cols_g_reais) == 1:
                        return df[[col_x, col_group]].dropna()
                    
                    df_melted = df.melt(value_vars=cols_x_reais, var_name='original_x_col', value_name='valores_temporarios')
                    df_melted[col_group] = df[cols_g_reais].bfill(axis=1).iloc[:, 0]
                    df_melted.rename(columns={'valores_temporarios': col_x}, inplace=True)
                    return df_melted.dropna(subset=[col_x, col_group])
                else:
                    if len(cols_x_reais) == 1:
                        return df[[col_x]].dropna()
                        
                    df_melted = df.melt(value_vars=cols_x_reais, var_name='original_x_col', value_name='valores_temporarios')
                    df_melted.rename(columns={'valores_temporarios': col_x}, inplace=True)
                    return df_melted.dropna(subset=[col_x])

            if (selected_variable_x or selected_variable_lat) and len(data_to_plot) > 0: 
                try:
if chart_type == "Barra":
                        plot_data = preparar_dados_plot(data_to_plot, selected_variable_x, selected_group_col)
                        
                        if selected_group_col and selected_group_col != "-- Nenhum --":
                            crosstab_counts = pd.crosstab(plot_data[selected_variable_x], plot_data[selected_group_col])
                            crosstab_perc = (crosstab_counts.div(crosstab_counts.sum(axis=1), axis=0) * 100).round(1)
                            plot_df = crosstab_perc.stack().reset_index()
                            plot_df.columns = [selected_variable_x, selected_group_col, 'Percentual']
                            fig = px.bar(plot_df, x=selected_variable_x, y='Percentual', color=selected_group_col, barmode='group', height=600)
                        else:
                            # --- CONSOLIDAÇÃO DE MÚLTIPLAS OPÇÕES ---
                            cols_x_reais = [c for c in data_to_plot.columns if c == selected_variable_x or c.startswith(f"{selected_variable_x}.")]
                            
                            if len(cols_x_reais) > 1:
                                series_consolidada = data_to_plot[cols_x_reais].stack()
                            else:
                                series_consolidada = data_to_plot[selected_variable_x]
                            
                            # --- TRATAMENTO DE TEXTO (Limpeza de Espaços e Padronização) ---
                            # Convertemos para string, removemos espaços invisíveis nas pontas e padronizamos em MAIÚSCULO
                            series_limpa = series_consolidada.astype(str).str.strip().str.upper()
                            
                            # Remove valores que fiquem vazios, nulos ou strings de erro comuns após a limpeza
                            series_limpa = series_limpa[~series_limpa.isin(['NAN', 'NONE', '', ' '])]
                            
                            # Agora sim, fazemos a contagem exata das categorias únicas
                            counts = series_limpa.value_counts().reset_index()
                            counts.columns = [selected_variable_x, 'Contagem']
                            
                            # Garante o agrupamento final e ordena do maior para o menor
                            counts = counts.groupby(selected_variable_x, as_index=False).sum()
                            counts = counts.sort_values(by='Contagem', ascending=False)
                            
                            fig = px.bar(counts, x=selected_variable_x, y='Contagem', text='Contagem', height=600)
                            fig.update_traces(textposition='outside')
                            
                        st.plotly_chart(fig, use_container_width=True)
    
                    elif chart_type == "Linha":
                        plot_data = preparar_dados_plot(data_to_plot, selected_variable_x)
                        if selected_variable_y == "Contagem":
                            plot_df = plot_data[selected_variable_x].value_counts().reset_index()
                            plot_df.columns = [selected_variable_x, 'Contagem']
                            y_ax = 'Contagem'
                        else:
                            plot_data[selected_variable_y] = data_to_plot[selected_variable_y]
                            plot_df = plot_data.groupby(selected_variable_x)[selected_variable_y].mean().reset_index()
                            y_ax = selected_variable_y

                        fig = px.line(plot_df, x=selected_variable_x, y=y_ax, markers=True)
                        st.plotly_chart(fig, use_container_width=True)

                    elif chart_type == "Pizza":
                        plot_data = preparar_dados_plot(data_to_plot, selected_variable_x)
                        plot_df = plot_data[selected_variable_x].value_counts().reset_index()
                        plot_df.columns = [selected_variable_x, 'count']
                        fig = px.pie(plot_df, names=selected_variable_x, values='count', hole=.3)
                        st.plotly_chart(fig, use_container_width=True)

                    elif chart_type == "Mapa": 
                        map_data = data_to_plot.copy()
                        map_data[selected_variable_lat] = pd.to_numeric(map_data[selected_variable_lat], errors='coerce')
                        map_data[selected_variable_lon] = pd.to_numeric(map_data[selected_variable_lon], errors='coerce')
                        map_data.dropna(subset=[selected_variable_lat, selected_variable_lon], inplace=True)
                        
                        fig = px.scatter_mapbox(map_data, lat=selected_variable_lat, lon=selected_variable_lon, 
                                                mapbox_style="carto-positron", zoom=3, height=600)
                        st.plotly_chart(fig, use_container_width=True)
                            
                except Exception as e:
                    st.error(f"Erro ao gerar gráfico: {e}")

            with st.expander("Ver Dados Filtrados"):
                st.dataframe(data_to_plot)

        except Exception as e:
            st.error(f"❌ Erro ao processar arquivo: {e}")
    else:
        st.info("Aguardando upload do arquivo CSV/TXT.")

# --- Inicialização Autônoma para Executável (.exe) ---
if __name__ == "__main__":
    if not st.runtime.exists():
        sys.argv = ["streamlit", "run", __file__, "--global.developmentMode=false"]
        sys.exit(stcli.main())
    else:
        main()

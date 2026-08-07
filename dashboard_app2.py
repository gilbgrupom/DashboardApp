import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
import os
import signal
import sys

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
    current_streamlit_pid = os.getpid() 

    col1, col2 = st.columns([1, 6])

    # Coluna da imagem (Logo)
    with col1:
        caminho_logo = resource_path("Logo_Pequena_Cinza.png")
        if os.path.exists(caminho_logo):
            st.image(caminho_logo, width=160)

    # Coluna do título
    with col2:
        st.title("Dashboard Avançado de Análise de Dados")

    # --- Captura da URL via Parâmetros query_params ---
    query_params = st.query_params
    api_url = query_params.get("api_data", None)

    # --- Sidebar para Ações de Sistema ---
    st.sidebar.header("Painel de Controle")
    if st.sidebar.button("❌ Encerrar Aplicativo"):
        if PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey('ctrl', 'w')
        try:
            os.kill(current_streamlit_pid, signal.SIGTERM)
            st.stop()
        except Exception as e:
            st.sidebar.error(f"Erro ao encerrar: {e}")

    # --- Carregamento Dinâmico de Dados ---
    data = None

    if api_url:
        with st.spinner("Carregando registros do banco de dados (Parcial Válido e Completo)..."):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*'
                }
                response = requests.get(api_url, headers=headers, timeout=15)
                if response.status_code == 200:
                    json_res = response.json()
                    if "data" in json_res and len(json_res["data"]) > 0:
                        data = pd.DataFrame(json_res["data"])
                        st.success(f"✅ **{len(data)}** registros carregados com sucesso!")
                    else:
                        st.warning("Nenhum registro encontrado com os status 'COMPLETO' ou 'PARCIAL VÁLIDO'.")
                else:
                    st.error(f"Erro na requisição HTTP: Código {response.status_code}")
            except Exception as e:
                st.error(f"Erro ao conectar com a API: {e}")
    else:
        st.info("💡 **Aguardando dados...** Acesse este aplicativo através do botão 'Dashboard' do painel para visualizar a análise.")

    # --- Processamento dos Dados ---
    if data is not None and not data.empty:
        
        # Pré-processamento de Latitude e Longitude
        col_com_separador = None
        for col in data.columns:
            s_limpo = data[col].astype(str).str.replace('(*)', '', regex=False)
            if s_limpo.str.contains('*', regex=False).any():
                amostra = s_limpo.dropna().iloc[0] if not s_limpo.dropna().empty else ""
                partes = amostra.split('*')
                if len(partes) == 2:
                    try:
                        float(partes[0].strip())
                        float(partes[1].strip())
                        col_com_separador = col
                        break
                    except ValueError:
                        continue

        if col_com_separador:
            try:
                partes_df = data[col_com_separador].astype(str).str.split('*', regex=False, expand=True)
                if partes_df.shape[1] >= 2:
                    data['latitude_processada'] = pd.to_numeric(partes_df[0], errors='coerce')
                    data['longitude_processada'] = pd.to_numeric(partes_df[1], errors='coerce')
            except Exception:
                pass

        # Nomes únicos de colunas
        raw_cols = []
        for col in data.columns:
            base_name = col.split('.')[0] if '.' in col and col.split('.')[-1].isdigit() else col
            raw_cols.append(base_name)
        
        unique_display_cols = sorted(list(set(raw_cols)))

        # ----------------------------------------------------------------------------------
        # SEÇÃO DE FILTROS AVANÇADOS
        # ----------------------------------------------------------------------------------
        st.header("1. Filtro de Dados (Opcional)")
        df_filtered = data.copy()

        col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
        
        with col_f1:
            filter_col = st.selectbox("Coluna para Filtrar:", options=["-- Nenhum Filtro --"] + unique_display_cols, index=0)
        
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
                with col_f2: op = st.selectbox("Operação para Múltiplas:", ["Contém a opção", "Não contém a opção"])
                with col_f3:
                    unique_vals = pd.unique(df_filtered[target_cols].values.ravel())
                    unique_vals = sorted([str(x) for x in unique_vals if pd.notna(x)])
                    val = st.selectbox("Selecione a Opção:", options=unique_vals)
                    condition = df_filtered[target_cols].isin([val]).any(axis=1)
                    df_filtered = df_filtered[condition] if op == "Contém a opção" else df_filtered[~condition]

            st.info(f"Total de registros filtrados: **{len(df_filtered)}**")
        else:
            st.info(f"Nenhum filtro aplicado. Total de registros: **{len(df_filtered)}**")

        data_to_plot = df_filtered 
        
        # ----------------------------------------------------------------------------------
        # CONFIGURAÇÃO E EXIBIÇÃO DOS GRÁFICOS
        # ----------------------------------------------------------------------------------
        st.header("2. Configuração da Visualização") 

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
                selected_variable_y = st.selectbox("Eixo Y:", options=["Contagem"] + numeric_cols)
        
        # --- FUNÇÃO AUXILIAR DE PREPARAÇÃO ---
        def preparar_dados_plot(df, col_x, col_group=None):
            cols_x_reais = [c for c in df.columns if c == col_x or c.startswith(f"{col_x}.")]
            if col_group and col_group != "-- Nenhum --":
                cols_g_reais = [c for c in df.columns if c == col_group or c.startswith(f"{col_group}.")]
                if len(cols_x_reais) == 1 and len(cols_g_reais) == 1:
                    df_res = df[[col_x, col_group]].dropna().copy()
                else:
                    df_res = df.melt(value_vars=cols_x_reais, var_name='original_x_col', value_name='valores_temporarios')
                    df_res[col_group] = df[cols_g_reais].bfill(axis=1).iloc[:, 0]
                    df_res.rename(columns={'valores_temporarios': col_x}, inplace=True)
                df_res[col_x] = df_res[col_x].astype(str).str.strip().str.upper()
                df_res[col_group] = df_res[col_group].astype(str).str.strip().str.upper()
                df_res = df_res[~df_res[col_x].isin(['NAN', 'NONE', '', ' '])]
                df_res = df_res[~df_res[col_group].isin(['NAN', 'NONE', '', ' '])]
                return df_res
            else:
                if len(cols_x_reais) == 1:
                    df_res = df[[col_x]].dropna().copy()
                else:
                    df_res = df.melt(value_vars=cols_x_reais, var_name='original_x_col', value_name='valores_temporarios')
                    df_res.rename(columns={'valores_temporarios': col_x}, inplace=True)
                df_res[col_x] = df_res[col_x].astype(str).str.strip().str.upper()
                df_res = df_res[~df_res[col_x].isin(['NAN', 'NONE', '', ' '])]
                return df_res

        # --- GERADOR DE GRÁFICOS ---
        st.header("3. Visualização") 

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
                        total_entrevistas = len(data_to_plot)
                        counts = plot_data[selected_variable_x].value_counts().reset_index()
                        counts.columns = [selected_variable_x, 'Contagem']
                        counts = counts.groupby(selected_variable_x, as_index=False).sum()
                        counts['Percentual'] = ((counts['Contagem'] / total_entrevistas) * 100).round(1)
                        counts = counts.sort_values(by='Percentual', ascending=False)
                        
                        fig = px.bar(counts, x=selected_variable_x, y='Percentual', 
                                     text=counts['Percentual'].astype(str) + '%', height=600,
                                     labels={'Percentual': 'Percentual sobre o Total (%)'})
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
                    total_entrevistas = len(data_to_plot)
                    plot_data = preparar_dados_plot(data_to_plot, selected_variable_x)
                    plot_df = plot_data[selected_variable_x].value_counts().reset_index()
                    plot_df.columns = [selected_variable_x, 'count']
                    plot_df = plot_df.groupby(selected_variable_x, as_index=False).sum()
                    plot_df['Percentual'] = ((plot_df['count'] / total_entrevistas) * 100).round(1)
                    plot_df = plot_df.sort_values(by='Percentual', ascending=False)
                    
                    fig = px.pie(plot_df, names=selected_variable_x, values='Percentual', hole=.3, height=600)
                    fig.update_traces(textinfo='label+percent', texttemplate='%{label}: %{value}%')
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

        with st.expander("Ver Tabela de Dados Carregada"):
            st.dataframe(data_to_plot)

# --- Inicialização ---
if __name__ == "__main__":
    if not st.runtime.exists():
        import streamlit.web.cli as stcli
        sys.argv = ["streamlit", "run", __file__, "--global.developmentMode=false"]
        sys.exit(stcli.main())
    else:
        main()


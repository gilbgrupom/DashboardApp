import os
import sys
import streamlit.web.cli as stcli
import multiprocessing
import webbrowser
from threading import Thread
import time

def resource_path(relative_path):
    """ Retorna o caminho absoluto para o recurso, funciona para dev e PyInstaller """
    try:
        # Pasta temporária onde o PyInstaller extrai os arquivos
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

def open_browser():
    """ Aguarda o servidor iniciar e abre o navegador """
    time.sleep(5)
    webbrowser.open("http://127.0.0.1:8501")

def main():
    # Caminho corrigido para o script do dashboard dentro do bundle
    script_path = resource_path("dashboard_app.py")
    
    # Define os argumentos para o Streamlit. 
    # É CRUCIAL definir developmentMode como false para evitar o erro da imagem.
    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--global.developmentMode=false",
        "--server.address=127.0.0.1",
        "--server.port=8501",
        "--server.headless=true",
    ]

    print("--- Inicializando Dashboard Analise Dados ---")
    
    # Thread para abrir o navegador automaticamente
    Thread(target=open_browser, daemon=True).start()

    # Executa o Streamlit diretamente via CLI interna
    try:
        stcli.main()
    except Exception as e:
        print(f"Erro crítico: {e}")
        time.sleep(10)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
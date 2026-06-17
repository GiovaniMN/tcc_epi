# Configuração de Software

## Pré-requisitos

*   Python 3.9 ou superior.
*   Ambiente virtual (recomendado).

## Instalação das Dependências

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
    cd SEU_REPOSITORIO
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Linux/Mac
    # venv\Scripts\activate   # Windows
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

    O arquivo `requirements.txt` inclui:
    *   `ultralytics`: Para inferência do modelo YOLO.
    *   `opencv-python`: Para captura e processamento de imagem.
    *   `firebase-admin`: Para comunicação com o Firebase.
    *   `requests`: Para envio de mensagens ao Telegram.
    *   `numpy`: Para operações numéricas.

    **Nota para Raspberry Pi:** A instalação do `ultralytics` e `opencv` pode demorar ou requerer pacotes de sistema adicionais.

## Estrutura de Pastas

*   `raspberry/coral_epi/`: Contém o script principal para execução na Raspberry Pi (`detect_zona.py`).
*   `src/`: Contém scripts de teste e versão para Windows (`deteccao_win.py`, `deteccao_pytorch.py`).
*   `models/`: Contém os modelos treinados (`.pt` e `.tflite`) e o arquivo de classes.
*   `config/`: Arquivos de configuração e chaves.

## Modelos

Certifique-se de que os modelos estejam nos caminhos esperados pelos scripts.
*   O script `detect_zona.py` (Raspberry Pi) espera o modelo TFLite em um caminho absoluto (ex: `/home/epirasp/Desktop/coral_epi/modelos/epi_full_integer_quant_edgetpu.tflite`). Você deve ajustar isso no arquivo de script ou organizar suas pastas conforme esperado.
*   O script `deteccao_win.py` (Windows) busca o modelo `epi.pt` na pasta `models/` relativa ao diretório de execução.

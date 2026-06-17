# Configuração do Sistema

Para que o sistema de monitoramento funcione corretamente, é necessário configurar as chaves de acesso do Firebase, o Token do Telegram e ajustar os caminhos dos arquivos.

## 1. Firebase

O sistema utiliza o Firebase Firestore para armazenar logs de alertas e o Firebase Storage (via base64 no Firestore ou similar) para imagens.

1.  Acesse o [Console do Firebase](https://console.firebase.google.com/).
2.  Crie um projeto ou selecione um existente.
3.  Vá em **Configurações do Projeto** > **Contas de Serviço**.
4.  Gere uma nova chave privada. Isso fará o download de um arquivo JSON.
5.  Renomeie este arquivo para `firebase_key.json`.
6.  Coloque este arquivo no diretório esperado pelo script:
    *   **Raspberry Pi:** O script `detect_zona.py` busca em `/home/epirasp/Desktop/coral_epi/firebase_key.json`. (Você deve editar o script para apontar para o local correto se for diferente).
    *   **Windows/Teste:** Coloque na raiz do projeto ou ajuste o caminho em `deteccao_win.py`.

## 2. Telegram Bot

O sistema envia notificações quando uma pessoa é detectada sem os EPIs necessários.

1.  Crie um bot no Telegram falando com o [@BotFather](https://t.me/BotFather).
2.  Obtenha o **Token** do bot.
3.  Obtenha o **Chat ID** para onde as mensagens serão enviadas (você pode usar o bot [@userinfobot](https://t.me/userinfobot) para descobrir seu ID).
4.  Atualize as variáveis na classe `Config` dentro dos scripts (`detect_zona.py` e `deteccao_win.py`):

    ```python
    class Config:
        TOKEN_TELEGRAM = 'SEU_TOKEN_AQUI'
        ID_CHAT_TELEGRAM = 'SEU_CHAT_ID_AQUI'
        # ...
    ```

## 3. Caminhos dos Arquivos (Configuração Crítica)

Os scripts possuem caminhos absolutos ou relativos "hardcoded" na classe `Config`. **Verifique e altere conforme seu ambiente.**

### Raspberry Pi (`raspberry/coral_epi/detect_zona.py`)
Por padrão, este script aponta para:
```python
CAMINHO_MODELO = '/home/epirasp/Desktop/coral_epi/modelos/epi_full_integer_quant_edgetpu.tflite'
CAMINHO_CLASSES = '/home/epirasp/Desktop/coral_epi/modelos/classes.txt'
CAMINHO_CHAVE_FIREBASE = '/home/epirasp/Desktop/coral_epi/firebase_key.json'
```
**Altere estes caminhos** para refletir onde você clonou o repositório na sua Raspberry Pi.

### Windows (`src/deteccao_win.py`)
Este script usa caminhos relativos, o que é mais flexível:
```python
MODEL_PATH = os.path.join(os.getcwd(), 'models', 'epi.pt')
# ...
```
Certifique-se de executar o script a partir da raiz do repositório para que `os.getcwd()` resolva corretamente.

## 4. Parâmetros de Detecção

Você pode ajustar a sensibilidade do sistema alterando os valores na classe `Config`:

*   `CONFIANCA_MINIMA`: Probabilidade mínima para considerar uma detecção válida.
*   `AREA_MINIMA` / `AREA_MAXIMA`: Filtra detecções muito pequenas (ruído) ou muito grandes.
*   `FRAMES_PESSOA_ESTAVEL`: Quantos frames consecutivos uma pessoa deve ser detectada para mudar o estado para "ENTRANDO".
*   `FRAMES_ANALISE_EPI`: Quantos frames são coletados para decidir se os EPIs estão presentes.

# Guia de Uso

Este documento explica como executar os scripts de detecção em diferentes ambientes.

## Executando na Raspberry Pi (Produção)

Este é o modo principal de operação, utilizando o acelerador Coral Edge TPU.

1.  Certifique-se de ter configurado o hardware e software conforme os guias [Hardware Setup](HARDWARE_SETUP.md) e [Software Setup](SOFTWARE_SETUP.md).
2.  Verifique se o arquivo `config/firebase_key.json` e os modelos estão nos caminhos corretos definidos no script `raspberry/coral_epi/detect_zona.py`.
3.  Execute o script:

    ```bash
    python raspberry/coral_epi/detect_zona.py
    ```

    O sistema irá:
    *   Iniciar a câmera.
    *   Conectar ao Firebase (para buscar zonas e enviar alertas).
    *   Iniciar o loop de detecção e a máquina de estados.
    *   Mostrar uma janela com o feed de vídeo e sobreposições (se houver monitor conectado).

## Executando no Windows / Teste (Sem Coral)

Para testes de lógica ou desenvolvimento em máquinas sem o acelerador Coral, utilize a versão Windows/PyTorch.

1.  Certifique-se de estar na raiz do projeto.
2.  Execute o script:

    ```bash
    python src/deteccao_win.py
    ```

    Este script utilizará o modelo `.pt` (PyTorch) padrão e a webcam do computador.

## Interface Web (Painel de Monitoramento)

O repositório contém uma pasta `sistema_de_monitoramento/` com arquivos HTML/JS para um dashboard.

Este painel é projetado para ser hospedado no Firebase Hosting. Ele permite visualizar o histórico de alertas salvos no Firestore.

Para visualizar localmente (apenas frontend, sem deploy):
Abra o arquivo `sistema_de_monitoramento/index.html` ou `sistema_de_monitoramento/dashboard.html` em seu navegador. *Nota: As funcionalidades que dependem de conexão com o Firebase precisarão das credenciais web configuradas corretamente nos arquivos JS.*

# Manual do Usuário - Jupiter Supervision

Este documento descreve como configurar e utilizar o sistema **Jupiter Supervision**, uma solução inteligente para detecção de Equipamentos de Proteção Individual (EPIs). O manual cobre a utilização da interface web e a execução do sistema de detecção no Raspberry Pi.

## Índice

1. [Interface Web (Sistema de Monitoramento)](#1-interface-web-sistema-de-monitoramento)
    - [Acesso](#acesso)
    - [Dashboard](#dashboard)
    - [Histórico de Ocorrências](#histórico-de-ocorrências)
    - [Configuração de Zona](#configuração-de-zona)
    - [Gerenciamento de Usuários](#gerenciamento-de-usuários)
2. [Sistema de Detecção (Raspberry Pi)](#2-sistema-de-detecção-raspberry-pi)
    - [Pré-requisitos](#pré-requisitos)
    - [Iniciando a Detecção](#iniciando-a-detecção)
    - [Funcionamento e Alertas](#funcionamento-e-alertas)

---

## 1. Interface Web (Sistema de Monitoramento)

O site, localizado na pasta `sistema_de_monitoramento`, é o painel de controle do sistema. Ele permite visualizar estatísticas, histórico de infrações e configurar as zonas de monitoramento.

### Acesso

Para acessar o sistema, abra o arquivo `index.html` em um navegador web ou acesse o endereço onde a aplicação foi implantada.

**Tela Inicial:** Apresenta uma visão geral do produto, recursos e tecnologia.
*   Clique em **"Acessar Sistema"** para fazer login.
*   Clique em **"Contato"** para enviar uma mensagem para a equipe de suporte.

### Login

Insira suas credenciais (e-mail e senha) na tela de login. O sistema utiliza autenticação via Firebase.

### Dashboard

Após o login, você será direcionado ao Dashboard (`dashboard.html`). Esta tela oferece:
*   **Visão Geral:** Estatísticas de detecções (total, EPIs faltantes).
*   **Gráficos:** Visualização da conformidade ao longo do tempo.
*   **Status do Sistema:** Indicadores de funcionamento.

### Histórico de Ocorrências

Acesse a página **Ocorrências** (`historico.html`) através do menu lateral.
*   Esta página lista todas as infrações detectadas pelo sistema.
*   Cada registro contém a data/hora, quais EPIs faltaram e uma imagem do momento da ocorrência.

### Configuração de Zona

Acesse a página **Configuração** (`configuracao.html`) para definir onde a câmera deve focar a detecção. Isso é crucial para evitar falsos positivos em áreas irrelevantes.

**Como configurar:**
1.  A página carregará a imagem mais recente capturada pelo sistema.
2.  Clique no botão **"Atualizar Imagem"** se necessário.
3.  **Desenhe a Zona:** Clique e arraste sobre a imagem para desenhar um retângulo verde. Esta será a área monitorada. A pessoa deve estar dentro desta área para ser analisada.
4.  Clique em **"Salvar Zona"** para aplicar as alterações. O sistema Raspberry Pi atualizará automaticamente suas configurações (pode levar alguns segundos).
5.  Use **"Limpar Zona"** se precisar refazer o desenho.

### Gerenciamento de Usuários

Na página **Usuários** (`usuarios.html`), administradores podem adicionar ou remover acesso de outros operadores do sistema.

---

## 2. Sistema de Detecção (Raspberry Pi)

O script de detecção roda diretamente no hardware (Raspberry Pi com Coral Edge TPU) e é responsável por processar o vídeo em tempo real.

### Pré-requisitos

*   Raspberry Pi configurado.
*   Acelerador Google Coral Edge TPU conectado.
*   Câmera conectada.
*   Ambiente virtual Python configurado na pasta `~/Desktop/coral_epi`.

### Iniciando a Detecção

Para iniciar o programa na Raspberry Pi, abra o terminal e execute os seguintes comandos:

```bash
cd Desktop/coral_epi
source venv/bin/activate
python detect_zona.py
```

### Funcionamento e Alertas

Ao iniciar, o programa abrirá uma janela mostrando o feed da câmera com as detecções sobrepostas.

**Condições para Detecção:**
*   **Posicionamento:** A pessoa deve estar de frente para a câmera.
*   **Distância:** A pessoa deve estar a uma distância aproximada de **4 a 5 metros** da câmera.
*   **Zona de Detecção:** A pessoa deve estar dentro da zona configurada (retângulo desenhado via site). Se nenhuma zona for configurada, a detecção pode ocorrer em toda a imagem, mas a precisão é melhor com a zona definida.

**Indicadores Visuais (Feedback):**
*   **Alerta Verde (Aprovado):** Se o usuário estiver utilizando todos os EPIs necessários (Capacete, Óculos e Botas), o sistema indicará conformidade.
*   **Alerta Vermelho (Rejeitado):** Se algum EPI estiver faltando, aparecerá um alerta vermelho na tela.

**Ações em Caso de Infrações:**
Se uma não conformidade for detectada (alerta vermelho):
1.  O sistema gera um registro contendo a **data e hora** da ocorrência.
2.  Lista os **EPIs que faltaram**.
3.  Captura uma **imagem** do momento exato.
4.  Envia esses dados para o **site** (visível na página de Ocorrências) e dispara uma notificação via **Telegram** (se configurado).

# Sistema de Monitoramento de EPIs com Visão Computacional 🛡️👁️

Este repositório contém o desenvolvimento de um sistema inteligente para monitoramento e fiscalização automática do uso de Equipamentos de Proteção Individual (EPIs). O projeto integra **Visão Computacional na Borda (Edge AI)**, **Internet das Coisas (IoT)** e **Serviços em Nuvem** para criar uma solução de baixo custo e alta eficiência para a segurança do trabalho.

## 📋 Resumo do Projeto

A segurança em ambientes industriais depende da conformidade rigorosa com normas de proteção. Este sistema visa automatizar a verificação de EPIs, eliminando a falibilidade da fiscalização manual. Utilizando uma arquitetura distribuída, o sistema processa imagens em tempo real em uma **Raspberry Pi 4**, acelerada por um **Google Coral Edge TPU**, e comunica infrações instantaneamente para supervisores via **Telegram**, enquanto mantém um registro auditável no **Firebase**.

O modelo de Inteligência Artificial foi treinado para detectar quatro classes fundamentais: **Pessoas**, **Capacetes**, **Óculos de Proteção** e **Botas de Segurança**.

---

## 🏗️ Arquitetura Técnica

O sistema foi projetado em uma arquitetura de três camadas: Borda, Lógica e Nuvem.

### 1. Hardware e Processamento na Borda
A base do sistema é uma **Raspberry Pi 4**, escolhida por sua versatilidade e conectividade. Para superar as limitações de processamento de CPU em inferências de redes neurais, foi acoplado um **Google Coral USB Accelerator**.
*   **Modelo:** YOLOv8n (Nano) quantizado para `int8` (Full Integer Quantization).
*   **Framework:** TensorFlow Lite (EdgeTPU Runtime).
*   **Multithreading:** O código (`raspberry/coral_epi/detect_zona.py`) implementa threads separadas para captura de vídeo (Webcam) e inferência, garantindo fluidez no processamento.

### 2. Lógica de Máquina de Estados
Para evitar falsos positivos e garantir que a análise ocorra apenas em momentos oportunos, o software implementa uma Máquina de Estados Finitos:
*   **VAZIO:** O sistema monitora a zona de interesse com baixo consumo.
*   **ENTRANDO:** Detecta a aproximação consistente de uma pessoa (validação por `FRAMES_PESSOA_ESTAVEL`).
*   **ANALISANDO:** Coleta amostras durante um período fixo (`FRAMES_ANALISE_EPI`), acumulando estatísticas de detecção dos EPIs.
*   **DECISÃO:** Compara a taxa de presença dos EPIs com o limiar configurado (`PROPORCAO_EPI_OK`).
    *   **APROVADO:** Feedback visual verde.
    *   **REJEITADO:** Feedback visual vermelho, disparo de foto para o Telegram e registro no banco de dados.
*   **SAINDO:** Aguarda a liberação da área para reiniciar o ciclo.

### 3. Integração em Nuvem
*   **Firebase Firestore:** Atua como backend NoSQL, armazenando logs de alertas (timestamp, EPIs faltantes) e configurações de zonas de detecção.
*   **Telegram Bot API:** Interface de notificação em tempo real. O sistema envia uma mensagem textual e a imagem da infração segundos após a detecção.
*   **Dashboard Web:** Uma interface frontend (`sistema_de_monitoramento/`) consome os dados do Firestore para gerar relatórios e visualizações gerenciais.

---

## 📊 Resultados e Performance

A validação do sistema demonstrou a viabilidade da aplicação de visão computacional na borda para este cenário.

### Métricas do Modelo (YOLOv8n)
O modelo alcançou uma precisão média (mAP@0.5) de **93.9%**, com destaque para a detecção de pessoas e capacetes.

| Classe | Precisão (P) | Revocação (R) | Análise |
| :--- | :---: | :---: | :--- |
| **Pessoa** | 97.4% | 90.8% | Alta confiabilidade, essencial para iniciar a máquina de estados. |
| **Capacete** | 96.9% | 91.4% | Classe com melhor distinção visual. |
| **Óculos** | 94.7% | 86.2% | Resultados robustos apesar da pequena área do objeto. |
| **Bota** | 89.7% | 80.9% | Desempenho satisfatório, com sensibilidade à oclusão. |

### Comparativo de Hardware (FPS)
Testes práticos revelaram o impacto crítico do acelerador de hardware:

*   **Com Coral Edge TPU:** O sistema mantém uma taxa estável entre **7 a 15 FPS**, suficiente para rastreamento em tempo real de pedestres.
*   **Sem Aceleração (CPU):** A performance cai para menos de **1 FPS**, inviabilizando a aplicação prática.
*   **Referência (PC i5-13500):** Atinge **30 FPS**, demonstrando a escalabilidade do software.

### Visualizações
<div align="center">
  <img src="models/yolov8n_pt/confusion_matrix_normalized.png" alt="Matriz de Confusão" width="45%">
  <img src="models/yolov8n_pt/results.png" alt="Curvas de Treinamento" width="45%">
</div>

---

## 📂 Estrutura do Repositório

Este repositório organiza os artefatos do projeto da seguinte forma:

*   `raspberry/coral_epi/`: Código fonte principal para execução na Raspberry Pi (Produção).
*   `src/`: Versões de teste e desenvolvimento para ambientes Windows/Linux (sem Coral).
*   `models/`: Arquivos binários dos modelos treinados (.pt e .tflite) e metadados de treinamento.
*   `sistema_de_monitoramento/`: Código fonte da interface web (Dashboard).
*   `docs/`: Documentação técnica detalhada da implementação.

---

## ✅ Conclusão

O projeto validou com sucesso a hipótese de que dispositivos de borda de baixo custo podem realizar fiscalização ativa de segurança. A combinação de **YOLOv8** com **Edge TPU** proveu o balanço ideal entre precisão e performance, enquanto a integração com **Telegram** e **Firebase** modernizou o fluxo de resposta a incidentes de segurança.

*Desenvolvido pelo Grupo 6 - Engenharia da Computação*

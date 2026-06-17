# Configuração de Hardware

Este projeto foi desenvolvido para rodar em uma **Raspberry Pi 4** com um acelerador **Google Coral Edge TPU (USB Accelerator)**.

## Requisitos de Hardware

*   **Raspberry Pi 4 Model B** (Recomendado 4GB ou 8GB de RAM)
*   **Google Coral USB Accelerator** (Edge TPU)
*   **Webcam** (USB) compatível com Raspberry Pi
*   Fonte de alimentação adequada para a Raspberry Pi (e hub USB alimentado se necessário para o Coral e Webcam)

## Montagem

1.  Conecte a Webcam a uma porta USB da Raspberry Pi.
2.  Conecte o Coral USB Accelerator a uma porta **USB 3.0** (azul) da Raspberry Pi para melhor performance.
3.  Certifique-se de que a Raspberry Pi tenha acesso à internet para enviar alertas ao Firebase e Telegram.

## Drivers do Coral Edge TPU

Para que o script de detecção funcione com o modelo `.tflite` quantizado para Edge TPU, é necessário instalar as bibliotecas de runtime do Coral.

Siga as instruções oficiais do Google ou execute os passos básicos abaixo (para Raspberry Pi OS 64-bit):

```bash
# Adicionar repositório Debian
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -

# Atualizar pacotes
sudo apt-get update

# Instalar runtime padrão
sudo apt-get install libedgetpu1-std

# (Opcional) Instalar runtime de performance máxima (pode esquentar mais)
# sudo apt-get install libedgetpu1-max
```

Após a instalação, verifique se o dispositivo é reconhecido.

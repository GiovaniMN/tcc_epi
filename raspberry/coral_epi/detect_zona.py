import cv2
import numpy as np
from ultralytics import YOLO
import time
from collections import deque, defaultdict
from threading import Thread, Lock
import firebase_admin
from firebase_admin import credentials, firestore
import requests
import logging
import os
from enum import Enum
import base64
from datetime import datetime

#configuracao de log para erross
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

#estados do controle de acesso
class EstadoEntrada(Enum):
    VAZIO = "VAZIO"
    ENTRANDO = "ENTRANDO"
    ANALISANDO = "ANALISANDO"
    APROVADO = "APROVADO"
    REJEITADO = "REJEITADO"
    SAINDO = "SAINDO"

#captura da camera
class CapturaCamera:
    def __init__(self, indice_camera=0):
        self.stream = cv2.VideoCapture(indice_camera)
        if not self.stream.isOpened():
            raise IOError("Camera indisponivel")
        
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.stream.set(cv2.CAP_PROP_FPS, 30)
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        ret, frame_teste = self.stream.read()
        if ret:
            largura_real = int(self.stream.get(cv2.CAP_PROP_FRAME_WIDTH))
            altura_real = int(self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.frame_atual = frame_teste
        self.lock_frame = Lock()
        self.parado = False
        
        self.thread_captura = Thread(target=self.atualizar_frames, daemon=True)
        self.thread_captura.start()

    def atualizar_frames(self):
        while not self.parado:
            ret, frame = self.stream.read()
            if ret:
                with self.lock_frame:
                    self.frame_atual = frame
            else:
                time.sleep(0.001)

    def obter_frame(self):
        with self.lock_frame:
            return self.frame_atual.copy() if self.frame_atual is not None else None

    def parar(self):
        self.parado = True
        if self.thread_captura.is_alive():
            self.thread_captura.join(timeout=0.5)
        if self.stream.isOpened():
            self.stream.release()

#configuracoes do sistema
class Config:
    TOKEN_TELEGRAM = '7683594838:AAFNpr3hQuKIlWK7MGg0kFnoxeZiA4k94OQ'
    ID_CHAT_TELEGRAM = '-1003141023291'
    
    CAMINHO_MODELO = '/home/epirasp/Desktop/coral_epi/modelos/epi_full_integer_quant_edgetpu.tflite'
    CAMINHO_CLASSES = '/home/epirasp/Desktop/coral_epi/modelos/classes.txt'
    CAMINHO_CHAVE_FIREBASE = '/home/epirasp/Desktop/coral_epi/firebase_key.json'
    
    RESOLUCAO_WEB = (640, 480)
    TAMANHO_INFERENCIA = (640, 640)
    
    CONFIANCA_MINIMA = {
        'pessoa': 0.30,
        'capacete': 0.58,
        'bota': 0.5,
        'oculos': 0.40
    }
    
    AREA_MINIMA = {
        'pessoa': 5500,
        'capacete': 500,
        'bota': 150,
        'oculos': 130
    }
    
    AREA_MAXIMA = {
        'pessoa': 150000,
        'capacete': 15000,
        'bota': 10000,
        'oculos': 8000
    }
    
    FRAMES_PESSOA_ESTAVEL = 8
    FRAMES_ANALISE_EPI = 20
    PROPORCAO_EPI_OK = 0.30
    FRAMES_SAIDA = 10
    
    #limites para mostrar na imagem do firebase
    PRESENCA_MINIMA_ALERTA = {
        'pessoa': 0.50,
        'capacete': 0.40,
        'bota': 0.5,
        'oculos': 0.4
    }
    
    CORES_ESTADOS = {
        EstadoEntrada.VAZIO: (128, 128, 128),
        EstadoEntrada.ENTRANDO: (255, 255, 0),
        EstadoEntrada.ANALISANDO: (255, 165, 0),
        EstadoEntrada.APROVADO: (0, 255, 0),
        EstadoEntrada.REJEITADO: (0, 0, 255),
        EstadoEntrada.SAINDO: (128, 0, 128)
    }
    
    CORES_EPIS = {
        'pessoa': (0, 255, 255),
        'capacete': (255, 0, 0),
        'bota': (0, 165, 255),
        'oculos': (255, 0, 255)
    }
    
    EPIS_OBRIGATORIOS = {'capacete', 'bota', 'oculos'}
    
    #ordem fixa dos nomes para dashboard
    ORDEM_EPIS_DASHBOARD = ['capacete', 'bota', 'oculos']

config = Config()

#rastreamento de deteccoes durante analise
class RastreadorDeteccoes:
    def __init__(self):
        self.reiniciar()
    
    def reiniciar(self):
        self.dados_por_classe = defaultdict(lambda: {
            'caixas': [],
            'confiancas': [],
            'total_frames': 0,
            'frames_detectados': 0,
            'caixa_media': None,
            'maior_confianca': 0.0
        })
        self.frames_analisados = 0
    
    def adicionar_frame(self, deteccoes):
        self.frames_analisados += 1
        
        for deteccao in deteccoes:
            if deteccao['na_zona']:
                classe = deteccao['classe']
                
                dados = self.dados_por_classe[classe]
                dados['caixas'].append(deteccao['bbox'])
                dados['confiancas'].append(deteccao['confianca'])
                dados['frames_detectados'] += 1
                dados['maior_confianca'] = max(dados['maior_confianca'], deteccao['confianca'])
        
        #atualizar total de frames para todas as classes
        for classe in ['pessoa', 'capacete', 'bota', 'oculos']:
            self.dados_por_classe[classe]['total_frames'] = self.frames_analisados
    
    def obter_deteccoes_confiaveis(self):
        deteccoes_validas = []
        
        for classe, dados in self.dados_por_classe.items():
            if dados['total_frames'] == 0:
                continue
            
            presenca = dados['frames_detectados'] / dados['total_frames']
            minimo_necessario = config.PRESENCA_MINIMA_ALERTA.get(classe, 0.30)
            
            if presenca >= minimo_necessario and dados['caixas']:
                bbox_media = self.calcular_bbox_media(dados['caixas'])
                
                deteccoes_validas.append({
                    'classe': classe,
                    'bbox': bbox_media,
                    'presenca': presenca,
                    'confianca_max': dados['maior_confianca'],
                    'frames_com': dados['frames_detectados'],
                    'total_frames': dados['total_frames'],
                    'confiavel': True
                })
        
        return deteccoes_validas
    
    def calcular_bbox_media(self, lista_bbox):
        if not lista_bbox:
            return None
        
        x1_total = y1_total = x2_total = y2_total = 0
        qtd = len(lista_bbox)
        
        for x1, y1, x2, y2 in lista_bbox:
            x1_total += x1
            y1_total += y1
            x2_total += x2
            y2_total += y2
        
        return (int(x1_total / qtd), int(y1_total / qtd),
                int(x2_total / qtd), int(y2_total / qtd))

#monitor de fps
class MostrarFPS:
    def __init__(self):
        self.tempos = deque(maxlen=30)
        self.ultima_atualizacao = 0
        self.fps_atual = 0
        
    def atualizar(self, tempo_frame):
        self.tempos.append(tempo_frame)
        if time.time() - self.ultima_atualizacao > 0.5:
            if len(self.tempos) >= 5:
                tempo_medio = sum(self.tempos) / len(self.tempos)
                self.fps_atual = 1.0 / tempo_medio if tempo_medio > 0 else 0
            self.ultima_atualizacao = time.time()
    
    def obter_fps(self):
        return self.fps_atual

#preprocessamento da imagem para o modelo
class PreparadorImagem:
    def __init__(self):
        self.tamanho_modelo = config.TAMANHO_INFERENCIA
        
    def preparar(self, frame):
        altura, largura = frame.shape[:2]
        escala = min(self.tamanho_modelo[0]/largura, self.tamanho_modelo[1]/altura)
        nova_largura, nova_altura = int(largura * escala), int(altura * escala)
        
        redimensionado = cv2.resize(frame, (nova_largura, nova_altura),
                                   interpolation=cv2.INTER_LINEAR)
        
        pad_topo = (self.tamanho_modelo[1] - nova_altura) // 2
        pad_base = self.tamanho_modelo[1] - nova_altura - pad_topo
        pad_esq = (self.tamanho_modelo[0] - nova_largura) // 2
        pad_dir = self.tamanho_modelo[0] - nova_largura - pad_esq
        
        com_padding = cv2.copyMakeBorder(redimensionado, pad_topo, pad_base,
                                        pad_esq, pad_dir, cv2.BORDER_CONSTANT,
                                        value=[114, 114, 114])
        
        return com_padding, escala, pad_topo, pad_esq

#controlador principal do sistema epi
class ControladorEPI:
    def __init__(self):
        self.firebase = GerenciadorFirebase()
        self.telegram = GerenciadorTelegram()
        self.preparador = PreparadorImagem()
        self.fps = MostrarFPS()
        self.rastreador = RastreadorDeteccoes()
        
        self.estado = EstadoEntrada.VAZIO
        self.tempo_estado = time.time()
        
        self.historico_pessoa = deque(maxlen=max(config.FRAMES_PESSOA_ESTAVEL, config.FRAMES_SAIDA))
        self.historico_epis = {epi: deque(maxlen=config.FRAMES_ANALISE_EPI)
                              for epi in config.EPIS_OBRIGATORIOS}
        
        self.deteccoes_cache = []
        self.contadores_cache = {}
        self.ultimo_alerta = 0
        self.frame_para_alerta = None
        
        #carregar modelo e classes
        self.modelo = YOLO(config.CAMINHO_MODELO, task='detect')
        with open(config.CAMINHO_CLASSES, "r") as arquivo:
            self.classes = arquivo.read().strip().split("\n")
        
        self.zonas = []
        self.ultima_busca_zonas = 0
        self.resolucao_camera = None
        self.contador_frames = 0

    def pular_frame(self):
        self.contador_frames += 1
        
        #economizar processamento quando nao ha pessoa
        if self.estado == EstadoEntrada.VAZIO:
            return self.contador_frames % 2 != 0
        elif self.estado == EstadoEntrada.ANALISANDO:
            return False
        elif self.estado in [EstadoEntrada.APROVADO, EstadoEntrada.REJEITADO]:
            return self.contador_frames % 2 != 0
        else:
            return False

    def detectar_objetos(self, frame):
        if self.pular_frame() and self.deteccoes_cache:
            return self.deteccoes_cache, self.contadores_cache
        
        try:
            frame_prep, escala, pad_y, pad_x = self.preparador.preparar(frame)
            
            resultados = self.modelo.predict(
                frame_prep, conf=0.1, iou=0.45, verbose=False,
                imgsz=640, device='cpu', half=False, augment=False
            )
            
            deteccoes = []
            contadores = defaultdict(int)
            
            if resultados and resultados[0].boxes is not None:
                for dados in resultados[0].boxes.data.cpu().numpy():
                    deteccao = self.processar_deteccao(dados, escala, pad_y, pad_x, frame.shape)
                    if deteccao:
                        deteccoes.append(deteccao)
                        if deteccao['na_zona']:
                            contadores[deteccao['classe']] += 1
            
            #armazenar frame limpo durante analise
            if self.estado == EstadoEntrada.ANALISANDO:
                self.rastreador.adicionar_frame(deteccoes)
                if self.frame_para_alerta is None:
                    self.frame_para_alerta = frame.copy()
            
            self.deteccoes_cache = deteccoes
            self.contadores_cache = dict(contadores)
            return deteccoes, contadores
            
        except Exception as e:
            logger.error(f"Erro na deteccao: {e}")
            return self.deteccoes_cache, self.contadores_cache

    def processar_deteccao(self, dados, escala, pad_y, pad_x, formato_frame):
        try:
            x1, y1, x2, y2, confianca, id_classe = dados
            classe = self.classes[int(id_classe)]
            
            #filtrar classes invalidas
            if classe not in config.EPIS_OBRIGATORIOS and classe != 'pessoa':
                return None
            #filtrar confianca baixa
            if confianca < config.CONFIANCA_MINIMA.get(classe, 0.5):
                return None
            
            #converter coordenadas para frame original
            x1 = (x1 - pad_x) / escala
            y1 = (y1 - pad_y) / escala
            x2 = (x2 - pad_x) / escala
            y2 = (y2 - pad_y) / escala
            
            x1 = max(0, min(int(x1), formato_frame[1] - 1))
            y1 = max(0, min(int(y1), formato_frame[0] - 1))
            x2 = max(0, min(int(x2), formato_frame[1] - 1))
            y2 = max(0, min(int(y2), formato_frame[0] - 1))
            
            #filtrar por area
            area = (x2 - x1) * (y2 - y1)
            if (area < config.AREA_MINIMA.get(classe, 0) or
                area > config.AREA_MAXIMA.get(classe, 999999)):
                return None
            
            #filtros especificos por classe
            if classe == 'pessoa':
                altura, largura = y2 - y1, x2 - x1
                if (altura <= 0 or largura <= 0 or
                    largura/altura > 2.8 or altura < formato_frame[0] * 0.07):
                    return None
            elif classe == 'oculos':
                centro_y = (y1 + y2) / 2
                if centro_y > formato_frame[0] * 0.65:
                    return None
            elif classe == 'bota':
                centro_y = (y1 + y2) / 2
                if centro_y < formato_frame[0] * 0.35:
                    return None
            
            return {
                'bbox': (x1, y1, x2, y2),
                'classe': classe,
                'confianca': float(confianca),
                'na_zona': self.esta_na_zona(x1, y1, x2, y2),
                'area': area
            }
        except:
            return None

    def esta_na_zona(self, x1, y1, x2, y2):
        if not self.zonas:
            return True
        
        centro_x = (x1 + x2) // 2
        centro_y = (y1 + y2) // 2
        
        for zona in self.zonas:
            if (zona['x'] <= centro_x <= zona['x'] + zona['largura'] and
                zona['y'] <= centro_y <= zona['y'] + zona['altura']):
                return True
        return False

    def atualizar_estado(self, contadores):
        tem_pessoa = contadores.get('pessoa', 0) > 0
        self.historico_pessoa.append(tem_pessoa)
        
        #verificar estabilidade da pessoa
        if len(self.historico_pessoa) >= config.FRAMES_PESSOA_ESTAVEL:
            frames_recentes = list(self.historico_pessoa)[-config.FRAMES_PESSOA_ESTAVEL:]
            pessoa_estavel = sum(frames_recentes) >= config.FRAMES_PESSOA_ESTAVEL * 0.75
        else:
            pessoa_estavel = False
            
        #verificar se pessoa esta saindo
        if len(self.historico_pessoa) >= config.FRAMES_SAIDA:
            frames_saida = list(self.historico_pessoa)[-config.FRAMES_SAIDA:]
            pessoa_saindo = sum(frames_saida) <= config.FRAMES_SAIDA * 0.25
        else:
            pessoa_saindo = False
        
        tempo_no_estado = time.time() - self.tempo_estado
        
        #maquina de estados
        if self.estado == EstadoEntrada.VAZIO:
            if pessoa_estavel:
                self.mudar_estado(EstadoEntrada.ENTRANDO)
                
        elif self.estado == EstadoEntrada.ENTRANDO:
            if not pessoa_estavel:
                self.mudar_estado(EstadoEntrada.VAZIO)
            elif tempo_no_estado >= 1.5:
                self.mudar_estado(EstadoEntrada.ANALISANDO)
                self.iniciar_analise()
                    
        elif self.estado == EstadoEntrada.ANALISANDO:
            if not pessoa_estavel:
                self.mudar_estado(EstadoEntrada.SAINDO)
            else:
                self.analisar_epis(contadores)
                        
        elif self.estado in [EstadoEntrada.APROVADO, EstadoEntrada.REJEITADO]:
            if pessoa_saindo:
                self.mudar_estado(EstadoEntrada.SAINDO)
                
        elif self.estado == EstadoEntrada.SAINDO:
            if not tem_pessoa and len(self.historico_pessoa) >= config.FRAMES_SAIDA:
                if not any(list(self.historico_pessoa)[-config.FRAMES_SAIDA:]):
                    self.mudar_estado(EstadoEntrada.VAZIO)

    def iniciar_analise(self):
        self.rastreador.reiniciar()
        self.frame_para_alerta = None
        for epi in config.EPIS_OBRIGATORIOS:
            self.historico_epis[epi].clear()

    def analisar_epis(self, contadores):
        for epi in config.EPIS_OBRIGATORIOS:
            self.historico_epis[epi].append(contadores.get(epi, 0) > 0)
        
        #verificar se temos dados suficientes
        amostras_minimas = min(len(hist) for hist in self.historico_epis.values() if hist)
        
        if amostras_minimas >= config.FRAMES_ANALISE_EPI:
            if self.todos_epis_ok():
                self.mudar_estado(EstadoEntrada.APROVADO)
            else:
                self.mudar_estado(EstadoEntrada.REJEITADO)
                self.enviar_alerta()

    def todos_epis_ok(self):
        for epi, historico in self.historico_epis.items():
            if not historico:
                return False
            proporcao = sum(historico) / len(historico)
            if proporcao < config.PROPORCAO_EPI_OK:
                return False
        return True

    def mudar_estado(self, novo_estado):
        if novo_estado != self.estado:
            print(f"Estado: {self.estado.value} → {novo_estado.value}")
            self.estado = novo_estado
            self.tempo_estado = time.time()

    def enviar_alerta(self):
        if time.time() - self.ultimo_alerta < 8:
            return
        
        #nomes em ordem fixa para dashboard
        epis_faltantes = []
        for epi in config.ORDEM_EPIS_DASHBOARD:
            historico = self.historico_epis.get(epi)
            if not historico:
                continue
            proporcao = sum(historico) / len(historico)
            if proporcao < config.PROPORCAO_EPI_OK:
                epis_faltantes.append(epi)
        
        if epis_faltantes:
            nomes = {'capacete': 'Capacete', 'bota': 'Bota', 'oculos': 'Óculos'}
            #manter ordem original dos faltantes
            faltantes = [nomes.get(epi, epi) for epi in epis_faltantes]
            mensagem = f"ACESSO NEGADO\nFaltando: {', '.join(faltantes)}"
            
            Thread(target=self.telegram.enviar, args=(mensagem,), daemon=True).start()
            Thread(target=self.salvar_alerta_firebase, args=(epis_faltantes, mensagem), daemon=True).start()
            
            self.ultimo_alerta = time.time()

    def criar_imagem_alerta(self):
        if self.frame_para_alerta is None:
            altura, largura = self.resolucao_camera[1], self.resolucao_camera[0]
            frame_alerta = np.zeros((altura, largura, 3), dtype=np.uint8)
        else:
            frame_alerta = self.frame_para_alerta.copy()
        
        deteccoes_confiaveis = self.rastreador.obter_deteccoes_confiaveis()
        
        #desenhar deteccoes na imagem
        for det in deteccoes_confiaveis:
            x1, y1, x2, y2 = det['bbox']
            classe = det['classe']
            confianca = max(0.0, min(1.0, det['confianca_max']))
            
            cor = config.CORES_EPIS.get(classe, (255, 255, 255))
            
            cv2.rectangle(frame_alerta, (x1, y1), (x2, y2), cor, 2)
            
            texto = f"{classe.upper()}: {confianca:.0%}"
            tamanho_texto = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            
            cv2.rectangle(frame_alerta, (x1, y1-28), (x1 + tamanho_texto[0] + 8, y1-2), cor, -1)
            cv2.putText(frame_alerta, texto, (x1 + 4, y1 - 8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        #timestamp
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        cv2.putText(frame_alerta, agora, (10, frame_alerta.shape[0] - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame_alerta

    def salvar_alerta_firebase(self, epis_faltantes, mensagem):
        try:
            imagem = self.criar_imagem_alerta()
            _, buffer = cv2.imencode('.jpg', imagem, [cv2.IMWRITE_JPEG_QUALITY, 90])
            imagem_b64 = base64.b64encode(buffer).decode('utf-8')
            
            dados = {
                'mensagem': mensagem,
                'epis_faltantes': epis_faltantes,
                'data_hora': datetime.now().isoformat(),
                'imagem_base64': imagem_b64
            }
            
            self.firebase.salvar_alerta(dados)
            
        except Exception as e:
            logger.error(f"Erro ao salvar alerta: {e}")

    def desenhar_interface(self, frame, deteccoes, contadores):
        display = frame.copy()
        altura, largura = display.shape[:2]
        
        cor_estado = config.CORES_ESTADOS.get(self.estado, (255, 255, 255))
        
        #desenhar zonas de deteccao
        for zona in self.zonas:
            cv2.rectangle(display, (zona['x'], zona['y']),
                         (zona['x'] + zona['largura'], zona['y'] + zona['altura']),
                         cor_estado, 3)
            
            overlay = display.copy()
            cv2.rectangle(overlay, (zona['x'], zona['y']),
                         (zona['x'] + zona['largura'], zona['y'] + zona['altura']),
                         cor_estado, -1)
            cv2.addWeighted(overlay, 0.25, display, 0.75, 0, display)
        
        #desenhar deteccoes em tempo real
        for det in deteccoes:
            if not det['na_zona']:
                continue
                
            x1, y1, x2, y2 = det['bbox']
            classe = det['classe']
            confianca = det['confianca']
            
            cor = config.CORES_EPIS.get(classe, (255, 255, 255))
            espessura = max(2, int(confianca * 3))
            
            cv2.rectangle(display, (x1, y1), (x2, y2), cor, espessura)
            
            texto = f"{classe.upper()}: {confianca:.2f}"
            tamanho = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            
            cv2.rectangle(display, (x1, y1-20), (x1 + tamanho[0] + 5, y1), cor, -1)
            cv2.putText(display, texto, (x1 + 2, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        #painel lateral com informacoes
        self.desenhar_painel_info(display, contadores, cor_estado)
        return display

    def desenhar_painel_info(self, frame, contadores, cor_estado):
        altura, largura = frame.shape[:2]
        largura_painel = 250
        x_painel = largura - largura_painel
        
        cv2.rectangle(frame, (x_painel, 0), (largura, 180), (25, 25, 25), -1)
        
        y = 25
        cv2.putText(frame, "CONTROLE EPI", (x_painel + 10, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y += 35
        
        fps_valor = self.fps.obter_fps()
        cv2.putText(frame, f"FPS: {fps_valor:.1f}", (x_painel + 10, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        y += 25
        
        cv2.circle(frame, (x_painel + 15, y + 5), 6, cor_estado, -1)
        cv2.putText(frame, self.estado.value, (x_painel + 30, y + 8),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor_estado, 1)
        y += 25
        
        #contadores das classes em ordem fixa
        for classe in ['pessoa', 'capacete', 'bota', 'oculos']:
            count = contadores.get(classe, 0)
            cor = config.CORES_EPIS.get(classe, (255, 255, 255))
            
            cv2.circle(frame, (x_painel + 12, y - 2), 4, cor, -1)
            cv2.putText(frame, f"{classe}: {count}", (x_painel + 25, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            y += 18

    def atualizar_zonas(self):
        if time.time() - self.ultima_busca_zonas > 25:
            try:
                zonas_firebase = self.firebase.obter_zonas()
                if zonas_firebase and self.resolucao_camera:
                    escala_x = self.resolucao_camera[0] / config.RESOLUCAO_WEB[0]
                    escala_y = self.resolucao_camera[1] / config.RESOLUCAO_WEB[1]
                    
                    self.zonas = []
                    for zona in zonas_firebase:
                        zona_convertida = {
                            'nome': zona.get('nome', 'ENTRADA'),
                            'x': int(zona['x'] * escala_x),
                            'y': int(zona['y'] * escala_y),
                            'largura': int(zona['width'] * escala_x),
                            'altura': int(zona['height'] * escala_y)
                        }
                        self.zonas.append(zona_convertida)
                    
                    if self.zonas:
                        print(f"Zona: {self.zonas[0]['largura']}x{self.zonas[0]['altura']}")
            except:
                pass
            self.ultima_busca_zonas = time.time()

    def executar(self):
        print("Iniciando detector EPI")
        
        try:
            camera = CapturaCamera(0)
            time.sleep(1.5)
            
            frame_teste = camera.obter_frame()
            if frame_teste is None:
                raise RuntimeError("Camera indisponivel")
            
            self.resolucao_camera = (frame_teste.shape[1], frame_teste.shape[0])
            print(f"Resolucao: {self.resolucao_camera}")
            
        except Exception as e:
            logger.error(f"Erro na camera: {e}")
            return

        cv2.namedWindow("Detector de EPI", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Detector de EPI", 800, 600)
        
        contador_frames = 0
        inicio = time.time()

        try:
            while True:
                inicio_loop = time.time()
                
                frame = camera.obter_frame()
                if frame is None:
                    continue
                
                contador_frames += 1
                
                #buscar zonas atualizadas periodicamente
                if contador_frames % 100 == 1:
                    self.atualizar_zonas()
                
                deteccoes, contadores = self.detectar_objetos(frame)
                self.atualizar_estado(contadores)
                
                frame_final = self.desenhar_interface(frame, deteccoes, contadores)
                cv2.imshow("Detector de EPI", frame_final)
                
                tempo_frame = time.time() - inicio_loop
                self.fps.atualizar(tempo_frame)
                
                #log periodico de performance
                if contador_frames % 500 == 0:
                    fps = self.fps.obter_fps()
                    minutos = (time.time() - inicio) / 60
                    print(f"FPS: {fps:.1f} | Estado: {self.estado.value} | {minutos:.1f}min")
                
                tecla = cv2.waitKey(1) & 0xFF
                if tecla == 27:
                    break
                elif tecla == ord('r'):
                    self.resetar_sistema()
                
        except KeyboardInterrupt:
            print("Sistema interrompido")
        finally:
            if contador_frames > 0:
                tempo_total = time.time() - inicio
                fps_medio = contador_frames / tempo_total
                print(f"FPS medio: {fps_medio:.2f}")
            
            camera.parar()
            cv2.destroyAllWindows()

    def resetar_sistema(self):
        self.estado = EstadoEntrada.VAZIO
        self.tempo_estado = time.time()
        self.historico_pessoa.clear()
        self.rastreador.reiniciar()
        self.frame_para_alerta = None
        for epi in config.EPIS_OBRIGATORIOS:
            self.historico_epis[epi].clear()

#gerenciador firebase
class GerenciadorFirebase:
    def __init__(self):
        self.db = None
        self.conectado = False
        self.inicializar()
    
    def inicializar(self):
        try:
            if not firebase_admin._apps:
                if not os.path.exists(config.CAMINHO_CHAVE_FIREBASE):
                    logger.error("Chave Firebase nao encontrada")
                    return
                    
                cred = credentials.Certificate(config.CAMINHO_CHAVE_FIREBASE)
                firebase_admin.initialize_app(cred)
                
            self.db = firestore.client()
            self.conectado = True
            print("Firebase conectado")
            
        except Exception as e:
            logger.error(f"Erro Firebase: {e}")
            self.conectado = False
    
    def esta_conectado(self):
        return self.conectado and self.db is not None
    
    def obter_zonas(self):
        if not self.esta_conectado():
            return []
        try:
            doc = self.db.collection('configuracoes').document('zones').get()
            return doc.to_dict().get('zones', []) if doc.exists else []
        except Exception as e:
            logger.error(f"Erro ao buscar zonas: {e}")
            return []
    
    def salvar_alerta(self, dados):
        if not self.esta_conectado():
            logger.warning("Firebase desconectado - alerta nao salvo")
            return
            
        try:
            self.db.collection('alertas_epi').add(dados)
            print("Alerta salvo no Firebase")
        except Exception as e:
            logger.error(f"Erro ao salvar alerta: {e}")

#gerenciador telegram
class GerenciadorTelegram:
    def __init__(self):
        self.sessao = requests.Session()
        self.sessao.timeout = 5
        
    def enviar(self, mensagem):
        if not config.TOKEN_TELEGRAM:
            return False
        try:
            url = f"https://api.telegram.org/bot{config.TOKEN_TELEGRAM}/sendMessage"
            dados = {'chat_id': config.ID_CHAT_TELEGRAM, 'text': mensagem}
            self.sessao.post(url, data=dados)
            return True
        except:
            return False

#funcao principal
def main():
    arquivos_necessarios = [config.CAMINHO_MODELO, config.CAMINHO_CLASSES]
    arquivos_faltando = [arq for arq in arquivos_necessarios if not os.path.exists(arq)]
    
    if arquivos_faltando:
        print(f"Arquivos nao encontrados: {arquivos_faltando}")
        return
    
    try:
        sistema = ControladorEPI()
        sistema.executar()
    except Exception as e:
        logger.error(f"Erro critico: {e}")

if __name__ == "__main__":
    main()

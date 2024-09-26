import serial
import time
import RPi.GPIO as GPIO
from statistics import mode
import logging

# Configurar o nível de log e o arquivo de saída
logging.basicConfig(filename='/home/aerador/Desktop/debug.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
# Criar um objeto de log
logger = logging.getLogger(__name__)

def contar_valores(arrays):
    # Inicializar contadores
    contador_0 = [0] * len(arrays[0])
    contador_1 = [0] * len(arrays[0])

    # Contar ocorrências
    for array in arrays:
        for i, valor in enumerate(array):
            if valor == 0:
                contador_0[i] += 1
            elif valor == 1:
                contador_1[i] += 1

    # Determinar os valores mais frequentes em cada posição
    valores_mais_frequentes = []
    for i in range(len(arrays[0])):
        if contador_0[i] > contador_1[i]:
            valores_mais_frequentes.append(0)
        elif contador_1[i] > contador_0[i]:
            valores_mais_frequentes.append(1)
        else:
            valores_mais_frequentes.append(0)  # Empate

    return valores_mais_frequentes

GPIO.setmode(GPIO.BCM)
GPIO.setup(21,GPIO.OUT)
GPIO.setup(20,GPIO.OUT)
GPIO.setup(16,GPIO.OUT)
GPIO.setup(26,GPIO.OUT)
GPIO.setup(19,GPIO.OUT)
GPIO.setup(13,GPIO.OUT)
GPIO.setup(6,GPIO.OUT)
GPIO.setup(5,GPIO.OUT)

GPIO.output(21,GPIO.HIGH)
GPIO.output(20,GPIO.HIGH)
GPIO.output(16,GPIO.HIGH)
GPIO.output(26,GPIO.HIGH)
GPIO.output(19,GPIO.HIGH)
GPIO.output(13,GPIO.HIGH)
GPIO.output(6,GPIO.HIGH)
GPIO.output(5,GPIO.HIGH)

time.sleep(5)
logger.info("inciando")

# Configuração da porta serial
port = '/dev/ttyS0'  # Porta serial a ser utilizada
baud_rate = 9600  # Taxa de transmissão em baud rate

# Inicialização da porta serial
ser = serial.Serial(port, baud_rate)

time.sleep(5)
print("iniciado")
logger.info("iniciado")

lmt_arranque = 30 # a cada 30 segundos verifica se deve arrancar 1 motor 
lmt_moda = 600 # a cada 5 minutos verifica a moda
dados = []
dados_complet = []
dados_manual = []
num_silos = 4 # quantos bits recebe por envio

#enviar = [0 for _ in range(num_silos)]
#enviar.insert(0,142)
#enviar = bytes(enviar) #se descomentar isso ele manda ligado por 1 segundo toda vez que liga o quadro de comando!
#ser.write(enviar)

inicio = time.time()
moda = [0 for _ in range(num_silos)]
temp_arranque_1 = time.time()
temp_moda_1 = time.time() 

# Loop principal
while True:
	try:
		# Verifica se há dados disponíveis para leitura na porta serial
		time.sleep(1)
		if ser.in_waiting > 0:
			#enviando sinal de online
			ser.write(bytes([17]))
			#enviando dados de ligado desligado para central
			enviar = [142,GPIO.input(21),GPIO.input(20),GPIO.input(16),GPIO.input(26)]
			ser.write(enviar)
			#reseta o tempo a cada sinal recebido
			inicio = time.time()
			# Lê os dados da porta serial para a parte automatica
			byte = ser.read(1)[0]

			if int(byte) == 170:
				bytes_auto = ser.read(num_silos)
				dados = [int(byte) for byte in bytes_auto]
				logger.info("dados:" +str(dados))
				dados_complet.append(dados)
				dados = []
			if int(byte) == 221:
				# Lê os dados da porta serial para a parte manual
				bytes_manual = ser.read(num_silos)
				dados_manual = [int(byte) for byte in bytes_manual]
				logger.info("dados_manual:" +str(dados_manual))

			print(dados_complet)
			print(dados_manual)

			temp_moda_2 = time.time()  
			
			#verifica se passou o tempo de contar moda
			if temp_moda_2 - temp_moda_1 > lmt_moda:
				#zerando contagem
				temp_moda_1 = time.time()
				# Transpor os dados para obter as colunas
				colunas = list(zip(*dados_complet))
				moda  = [mode(coluna) for coluna in colunas]
				dados_complet = []
				logger.info("moda:" +str(moda))
				print(moda)

			temp_arranque_2 = time.time()  

			print(temp_arranque_2 - temp_arranque_1)

			if temp_arranque_2 - temp_arranque_1 > lmt_arranque:
					#zerando contagem
					temp_arranque_1 = time.time()

					# DELIGANDO AERADORES

					if (moda[0] == 0 and dados_manual[0] == 0) or dados_manual[0] == 2:
						GPIO.output(21,GPIO.HIGH)
						
					if (moda[1] == 0 and dados_manual[1] == 0) or dados_manual[1] == 2:
						GPIO.output(20,GPIO.HIGH)
						
					if (moda[2] == 0 and dados_manual[2] == 0) or dados_manual[2] == 2:	
						GPIO.output(16,GPIO.HIGH)
						
					if (moda[3] == 0 and dados_manual[3] == 0) or dados_manual[3] == 2:
						GPIO.output(26,GPIO.HIGH)				

					# LIGANDO AERADORES

					if (moda[0] == 1 or dados_manual[0] == 3) and GPIO.input(21) == GPIO.HIGH and dados_manual[0] != 2:
						GPIO.output(21,GPIO.LOW)
						continue	
						
					if (moda[1] == 1 or dados_manual[1] == 3) and GPIO.input(20) == GPIO.HIGH and dados_manual[1] != 2:
						GPIO.output(20,GPIO.LOW)
						continue
						
					if (moda[2] == 1 or dados_manual[2] == 3) and GPIO.input(16) == GPIO.HIGH and dados_manual[2] != 2:
						GPIO.output(16,GPIO.LOW)
						continue
						
					if (moda[3] == 1 or dados_manual[3] == 3) and GPIO.input(26) == GPIO.HIGH and dados_manual[3] != 2:
						GPIO.output(26,GPIO.LOW)
						continue

		else:
			fim = time.time()
			if fim - inicio > 60: # desliga em 1 min sem receber sinal
				moda = [0 for _ in range(num_silos)]
				dados_manual = [0,0,0,0]
				GPIO.output(21,GPIO.HIGH)
				GPIO.output(20,GPIO.HIGH)
				GPIO.output(16,GPIO.HIGH)
				GPIO.output(26,GPIO.HIGH)
				GPIO.output(19,GPIO.HIGH)
				GPIO.output(13,GPIO.HIGH)
				GPIO.output(6,GPIO.HIGH)
				GPIO.output(5,GPIO.HIGH)

	except Exception as e:
		logger.info("Erro: "+str(e))
		

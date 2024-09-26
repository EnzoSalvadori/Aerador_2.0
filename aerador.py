from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, login_required, UserMixin, login_user, logout_user
import requests
from flask_socketio import SocketIO
import pandas as pd
import serial
import webbrowser
import sqlite3
import rsa
from datetime import datetime
import time
import logging
import socket
import selectors
import urllib.parse
import threading

# Configurações receber estação
HOST = '0.0.0.0'  # Escuta em todas as interfaces (de preferencia colocar o IP da estação)
PORT = 8080       # Porta para escutar

# Cria um seletor
sel = selectors.DefaultSelector()

# Cria um socket para TCP
tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_socket.bind((HOST, PORT))
tcp_socket.listen()
tcp_socket.setblocking(False)
sel.register(tcp_socket, selectors.EVENT_READ, data="tcp")

# Variáveis globais para armazenar os últimos valores
latest_temp = None
latest_humidity = None
latest_rainin = None

# Função para processar a linha de requisição GET
def process_get_line(get_line):
    # Extrai a parte da URL após "GET "
    request = get_line.split(' ')[1]
    # Parseia a URL para obter os parâmetros
    query = urllib.parse.urlsplit(request).query
    params = urllib.parse.parse_qs(query)
    # Extrai temperatura, umidade e precipitação, se disponíveis
    temp = params.get('tempf', ['N/A'])[0]
    humidity = params.get('humidity', ['N/A'])[0]
    rainin = params.get('rainin', ['N/A'])[0]
    return temp, humidity, rainin

# Função para identificar e processar pacotes
def identify_packet():
    global latest_temp, latest_humidity, latest_rainin
   
    while True:
        try:
            events = sel.select(timeout=None)
            for key, _ in events:
                if key.data == "tcp":
                    conn, addr = key.fileobj.accept()
                    data = conn.recv(1024).decode()
                    #print(f"Recebido pacote TCP de {addr}: {data}")
                    # Procura pela linha de requisição GET
                    for line in data.splitlines():
                        if line.startswith('GET'):
                            temp, humidity, rainin = process_get_line(line)
                            latest_temp = temp
                            latest_humidity = humidity
                            latest_rainin = rainin
                            #print(f"Temperatura: {temp} °F, Umidade: {humidity} %, Precipitação: {rainin} mm")
                    conn.close()
        except:
            print("Pacote errado ...")

# Configurar o nível de log e o arquivo de saída
logging.basicConfig(filename='debug.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
# Criar um objeto de log
logger = logging.getLogger(__name__)

# Crie uma instância do Flask
app = Flask(__name__)
#criando um socket para atualizaçao automatica
app.config['SECRET_KEY'] = 'S@fr@2023'
socketio = SocketIO(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Rota para redirecionar em caso de acesso não autorizado

#lendo os valores guardados no banco de dados
banco  = sqlite3.connect("config.db")
cursor = banco.cursor()

cursor.execute("SELECT * FROM opts")
opts = cursor.fetchall()

#tabela de configuraçoes
Nsilos = opts[0][0]
API_EST = opts[0][2]

#tabela de estado do aerador
global LD_silos
global LD_silos_old
LD_silos = []
for i in range(Nsilos):
    LD_silos.append(0)
LD_silos_old =LD_silos

#configurações de Online e Offline
global ONLINE
global ONLINE_old
global tOn
global tOff
ONLINE = False
ONLINE_old = True
tOn = time.time()  
tOff = time.time()  

# Configuração da porta serial

#PORTA SERIAL    
global ser
global port

port = opts[0][1]  # Porta serial a ser utilizada
baud_rate = 9600  # Taxa de transmissão em baud rate

# Fechando a conexão
banco.close()

# Carrega a chave RSA privada
with open("private_key.pem", "rb") as private_key_file:
    private_key_data = private_key_file.read()
    private_key = rsa.PrivateKey.load_pkcs1(private_key_data)

try:
    # Inicialização da porta serial
    ser = serial.Serial(port, baud_rate)
except:
    print("SERIAL NAO CONECTADO")

def registrar_maquina(liga_desliga,maquina_nome):
    banco  = sqlite3.connect("config.db")
    cursor = banco.cursor()
    ligar_timestamp = datetime.now()
    cursor.execute(f'''
        INSERT INTO tempo_uso_{maquina_nome} (data,liga_desliga) VALUES (?,?)
    ''', (ligar_timestamp,liga_desliga))
    #salvando banco
    banco.commit()
    # Fechando a conexão
    banco.close()

# Classe de exemplo que representa um usuário
class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

# Função para buscar usuário pelo ID (simulando o banco de dados)
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Defina as rotas e as funções de visualização abaixo

# Rota de login
@app.route('/login', methods=["GET","POST"])
def login():
    #lendo os valores guardados no banco de dados
    banco  = sqlite3.connect("config.db")
    cursor = banco.cursor()
    cursor.execute("SELECT * FROM login")
    lgn = cursor.fetchall()
    # Fechando a conexão
    banco.close()
    user_id = 1  # ID do usuário autenticado (você obteria isso após a autenticação)

    if request.remote_addr == "127.0.0.1":
        user = User(user_id)
        login_user(user)
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        senha_descriptografada = rsa.decrypt(lgn[0][1], private_key)
        usuario = lgn[0][0]
        if usuario == username and senha_descriptografada == password.encode():
            user = User(user_id)
            login_user(user)
            return redirect(url_for('home'))
        else:
            return render_template('login.html')
    else:
        return render_template('login.html')
    
    
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# Rota principal
@app.route('/', methods=["GET","POST"])
@login_required
def home():
    #abrindo conexão com banco de dados
    banco  = sqlite3.connect("config.db")
    cursor = banco.cursor()
    
    #valor da tabela desenhada
    cultivo = "Soja"
    tabela = pd.read_excel('tabelas/'+str(cultivo)+'.xlsx') 
    tabela = tabela.astype(str)
    
    if request.method == "GET": 
        cultivo = request.args.get('cultivo')
        if cultivo != None:
            tabela = pd.read_excel('tabelas/'+str(cultivo)+'.xlsx') 
            tabela = tabela.astype(str)  
        else:
            cultivo = "Soja"
    
    if request.method == "POST":
        for i in range(Nsilos):
            num = i+1
            prod = request.form.get("silo"+str(num))
            nme = "Silo_"+str(num)
            cursor.execute("UPDATE silos SET Produto = (?) WHERE Nome = (?)",(prod,nme))

    #salvando banco
    banco.commit()
    # Fechando a conexão
    banco.close()

    return render_template('base.html', tabela=tabela , cultivo=cultivo , Nsilos=Nsilos)
    
@app.route('/config', methods=["GET","POST"])
@login_required
def config():
    return render_template('config.html', Nsilos=Nsilos)

@app.route('/grafico', methods=['GET', 'POST'])
def grafico():
    banco  = sqlite3.connect("config.db")
    cursor = banco.cursor()

    selected_day = request.form.get('selected_day', '')
    selected_silo = request.form.get('selected_silo', '')

    if selected_day and selected_silo:
        selected_silo = int(selected_silo)
        TABLE_NAME = 'tempo_uso_'+str(selected_silo-1)
        cursor.execute(f'SELECT * FROM {TABLE_NAME} WHERE DATE(data) = ?', (selected_day,))
    else:
        TABLE_NAME = 'tempo_uso_'+str(0)
        cursor.execute(f'SELECT * FROM {TABLE_NAME} WHERE DATE(data) = ?', (datetime.now(),))

    data = cursor.fetchall()
    #salvando banco
    banco.commit()
    # Fechando a conexão
    banco.close()

    # Preparar dados para o gráfico
    x_values = [datetime.strptime(entry[0], '%Y-%m-%d %H:%M:%S.%f') for entry in data]
    y_values = [entry[1] for entry in data]

    try:
        objeto_original = x_values[0]

        # Criar cópia com a mesma data, mas com a hora 00:00:00
        copia_hora_zero = datetime(objeto_original.year, objeto_original.month, objeto_original.day)
        # Criar cópia com a mesma data, mas com a hora de agora
        copia_hora_now = datetime(objeto_original.year, objeto_original.month, objeto_original.day, 
                                             datetime.now().hour, datetime.now().minute, datetime.now().second)
        # Criar cópia com a mesma data, mas com a hora 23:59:59
        copia_hora_vinte_e_quatro = datetime(objeto_original.year, objeto_original.month, objeto_original.day, 23, 59, 59)

        x_values.insert(0,copia_hora_zero) #inserir na posição 0
        y_values.insert(0,0)
        x_values.append(copia_hora_now) #inserir na posição final
        y_values.append(0)
        x_values.append(copia_hora_vinte_e_quatro) #inserir na posição final
        y_values.append(0)

    except Exception as e:
        print(e)

    print(x_values)

    # Calcular a diferença em horas entre os pontos consecutivos onde o valor é 1 (ligado)
    total_time_on = datetime.strptime('00:00:00', '%H:%M:%S')
    for i in range(len(x_values) - 1):
        if y_values[i] == 1:
            time_difference = x_values[i + 1] - x_values[i]
            total_time_on += time_difference

    total_time_on_formatted = total_time_on.strftime('%H:%M:%S')

    # Convertendo para o formato de hora, minuto e segundo para o grafico
    formatted_x_values = [entry.strftime('%H:%M:%S') for entry in x_values]

    return render_template('grafico.html', x_values=formatted_x_values, y_values=y_values, selected_day=selected_day,selected_silo=selected_silo,Nsilos=Nsilos,total_time_on_formatted=total_time_on_formatted)

#função apra descidir qual sinal enviar
def autoLD(equilibrios,estados,min,max,temp_max,temperaturaG):
    temperaturaG += 3 #vetiladores esquenta em 2 graus a temperatura do ar
    sinal = []
    sinal.append(170)
    for i in range(len(estados)):
        if float(equilibrios[i]) >= float(min[i]) and float(equilibrios[i]) <= float(max[i]) and (temperaturaG <= float(temp_max[i])):
            sinal.append(1)
        else:
            sinal.append(0)

    sinal.append(221)
    for i in range(len(estados)):
        if estados[i] == "ligado":
            sinal.append(3)
        elif estados[i] == "desligado":
            sinal.append(2)
        else:
            sinal.append(0)
			
    return sinal

#calculando equilibrio hidroscopico
def equilibrioHidro(temperatura,umidade,produto):
   
    aux = 0
    cont = -1
    df = pd.read_excel("tabelas/"+str(produto)+'.xlsx')
       
    if temperatura < 12:
        temperatura = 12.0
                
    if temperatura > 33:
        temperatura = 33.0

    if umidade < 50:
        umidade = 50

    for i in df['-']:
        i = i.split('%')[0]
        cont += 1
        if int(umidade) < int(i):
            dif = int(i)-int(umidade) 
            passo = (df[temperatura][cont] - df[temperatura][cont-1])/5
            return round(df[temperatura][cont]-(passo*dif),2),[cont,cont+1],df.columns.get_loc(temperatura)
        if int(umidade) == int(i):
            return df[temperatura][cont],[cont+1],df.columns.get_loc(temperatura)
                    
#enviando sinal feito na função autoLD
def emitirSinal(sinal,precipitaçãoG):
    #PORTA SERIAL    
    global ser
    global port

    # se estiver chovendo envia sinal para desligar tudo 0000-2222
    if precipitaçãoG > 0:
        SNL = int(len(sinal)/2)-1
        for i in range(SNL):
            sinal[i+1] = 2
            sinal[i+SNL+2] = 2

    dados = bytes(sinal)
    try:
        ser.write(dados)
        logger.info('Enviando dados para comando: '+ str(dados))
        print(dados)

    except:
        print("SERIAL NAO CONECTADO")
        # Reinicialização da porta serial
        try:
            ser.close()
            # Inicialização da porta serial
            ser = serial.Serial(port, baud_rate)
        except:
            print("TENTATIVA DE CONEXÂO FALHA")
        print(dados)

def receberSinal():
    try:
        global ONLINE
        global ONLINE_old
        global tOn
        global tOff
        global LD_silos
        while True:
            try:
                time.sleep(1)
                tOff = time.time()  
                if abs(tOn - tOff) > 60:
                    ONLINE_old = ONLINE
                    ONLINE = False
                if ONLINE == False:
                    
                    print("OFFLINE")
                    if  ONLINE_old == True:
                        #zerando todos os pontos como deligados
                        for i in range(Nsilos):
                            registrar_maquina(0,i)
                #verificando se foi ligado ou desligado algum motor
                if ser.in_waiting > 0:
                    byte = ser.read(1)[0]
                    #logger.info('Byte recebido: '+ str(byte))
                    if ser.in_waiting > 1:
                        if int(byte) == 142:
                            try:
                                LD_silos = ser.read(Nsilos)
                                # Invertendo os valores dos bytes
                                LD_silos = bytes([1 - b for b in LD_silos])
                                # Convertendo para uma lista de inteiros
                                LD_silos = [int(byte) for byte in LD_silos]
                                print(LD_silos)
                                for i in range(Nsilos):
                                    # se o valor esta diferente do antigo ele mudou de ligado para desligado ou o contrario 
                                    if LD_silos[i] != LD_silos_old[i]:
                                        LD_silos_old[i] = LD_silos[i]
                                        registrar_maquina(LD_silos[i],i)

                                logger.info('Dados recebidos: '+ str(LD_silos))
                            except Exception as e:
                                print(e)
                    if int(byte) == 17:
                        ONLINE_old = ONLINE
                        ONLINE = True
                        print("ONLINE")
                        tOn = time.time()  

                    if int(byte) != 17 and int(byte) != 142:
                        logger.info('DADO DESCONHECIDO:'+ str(byte))
                        print("DADO DESCONHECIDO:" + str(byte))

            except Exception as e:
                print(e)
                print("SEM RECEBER DADOS")
    except:
        socketio.start_background_task(receberSinal)


def atualizardados():
    try:
        #abrindo conexão com banco de dados
        banco  = sqlite3.connect("config.db")
        cursor = banco.cursor()
        global LD_silos

        while True:
            try:
                if latest_temp != 'N/A' and latest_temp != None:
                    print("ENTROU")
                    umidadeG = float(latest_humidity)
                    temperaturaG = (float(latest_temp) - 32) * 5.0/9.0
                    precipitaçãoG = float(latest_rainin)
                   
                    umidadeG = round(umidadeG)
                    temperaturaG = round(temperaturaG)

                    cursor.execute("SELECT * FROM silos")
                    resultados  = cursor.fetchall()

                    # Transformando os resultados em uma lista de dicionários
                    colunas = [coluna[0] for coluna in cursor.description]
                    silos = [dict(zip(colunas, linha)) for linha in resultados]

                    dados_emitir = {
                            "numSilos":Nsilos,
                            "temperatura":temperaturaG,
                            "umidade":umidadeG,
                            "produto": [],
                            "estado": [],
                            "min": [],
                            "max": [],
                            "temp_max": [],
                            "equilibrioHidro": [],
                            "sinal": [],
                            "ponto": [],
                            "ONLINE": [],
                            "LD_silos":[],
                    }

                    #inserindo os dados e calculando
                        
                    for silo in silos:
                        dados_emitir["produto"].append(silo["Produto"])
                        dados_emitir["estado"].append(silo["Estado"])
                        dados_emitir["min"].append(silo["Min"])
                        dados_emitir["max"].append(silo["Max"])
                        dados_emitir["temp_max"].append(silo["TempMax"])

                    if umidadeG < 50 or temperaturaG < 12 or temperaturaG > 33:
                        eqlbr = []
                        for prd in dados_emitir["produto"]:
                            dados_emitir["equilibrioHidro"].append("FORA DA ESCALA")
                            eqlbr.append(0)
                        sinal = autoLD(eqlbr,dados_emitir["estado"],dados_emitir["min"],dados_emitir["max"],dados_emitir["temp_max"],temperaturaG)
                        dados_emitir["sinal"] = sinal
                        dados_emitir["ONLINE"] = ONLINE
                        dados_emitir["LD_silos"] = LD_silos
                        emitirSinal(sinal,precipitaçãoG)
        
                    else:   
                        for prd in dados_emitir["produto"]:
                            eq,linha,coluna = equilibrioHidro(temperaturaG, umidadeG, prd)
                            dados_emitir["equilibrioHidro"].append(float(eq))
                                
                        dados_emitir["ponto"].append([linha,coluna])
                        sinal = autoLD(dados_emitir["equilibrioHidro"],dados_emitir["estado"],dados_emitir["min"],dados_emitir["max"],dados_emitir["temp_max"],temperaturaG)
                        dados_emitir["sinal"] = sinal
                        dados_emitir["ONLINE"] = ONLINE
                        dados_emitir["LD_silos"] = LD_silos
                        emitirSinal(sinal,precipitaçãoG)

                    #alertar a principio de chuva
                    if precipitaçãoG > 0:
                        for silo in silos:
                            silo["Estado"] = 2

                    socketio.emit('atualizar', dados_emitir)
                    
                socketio.sleep(5)    

            except Exception as e:

                print(e)

                #enviando sinal desligado para maquina
                for i in range(Nsilos):
                    registrar_maquina(0,i)

                dados_emitir = {
                            "numSilos":Nsilos,
                            "temperatura":"OFFLINE ",
                            "umidade":"OFFLINE",
                            "produto": [],
                            "estado": [],
                            "min": [],
                            "max": [],
                            "temp_max": [],
                            "equilibrioHidro": [],
                            "sinal": [],
                            "ponto": [],
                            "ONLINE": [],
                            "LD_silos":[],
                }

                zeros = []
                sinal = []
                for i in range(Nsilos):
                    zeros.append(0)

                sinal.append(170)
                sinal.extend(zeros)
                sinal.append(221)
                sinal.extend(zeros)
                emitirSinal(sinal,precipitaçãoG)
                socketio.emit('atualizar', dados_emitir)

                socketio.sleep(5) 

    except Exception as e:
        print(e)
        socketio.start_background_task(atualizardados)

#cria uma rotina de atualizar dados
socketio.start_background_task(atualizardados)
#cria uma rotina de atualizar dados
socketio.start_background_task(receberSinal)

#definindo MAX e MIN
@socketio.on('MaxMin')
def updateMaxMin(mensagem):
    #abrindo conexão com banco de dados
    banco  = sqlite3.connect("config.db")
    cursor = banco.cursor()

    campo = mensagem[:3]
    numero = mensagem[3:4]
    valor = mensagem.split('|')[1]
    nme = "Silo_"+numero
    if campo == "Max":
         cursor.execute("UPDATE silos SET Max = (?) WHERE Nome = (?)",(valor,nme))
    elif campo == "Min":
         cursor.execute("UPDATE silos SET Min = (?) WHERE Nome = (?)",(valor,nme))
    elif campo == "Tmp":
         cursor.execute("UPDATE silos SET TempMax = (?) WHERE Nome = (?)",(valor,nme))
    #salvando banco
    banco.commit()
    # Fechando a conexão
    banco.close()
    
#definindo LIG/DES/AUTO
@socketio.on('siloBtn')
def siloData(mensagem):
    #abrindo conexão com banco de dados
    banco  = sqlite3.connect("config.db")
    cursor = banco.cursor()

    mapeamento = {
        "Desligar": "desligado",
        "Ligar": "ligado",
        "Automatico": "automatico"
    }

    for silo in range(1, Nsilos+1):
        if any(comando in mensagem and f"s{silo}" in mensagem for comando in mapeamento.keys()):
            estado = mapeamento[next(comando for comando in mapeamento.keys() if comando in mensagem)]
            nme = f"Silo_{silo}"
            cursor.execute("UPDATE silos SET Estado = (?) WHERE Nome = (?)",(estado,nme))
    #salvando banco
    banco.commit()
    # Fechando a conexão
    banco.close()
    
# Execute o aplicativo Flask
if __name__ == '__main__':
    webbrowser.open("http://127.0.0.1:5000/")
    # Cria threads para rodar as funções em paralelo
    packet_thread = threading.Thread(target=identify_packet)
    # Inicia as threads
    packet_thread.start()
    socketio.run(app,host="0.0.0.0",port="5000")
    # Aguarda as threads terminarem (tecnicamente não terminarão até o encerramento do programa)
    packet_thread.join()
    
    

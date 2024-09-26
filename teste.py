import socket
import selectors
import urllib.parse
import threading
import time

# Configurações receber estação
HOST = '0.0.0.0'  # Escuta em todas as interfaces
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
    try:
        while True:
            events = sel.select(timeout=None)
            for key, _ in events:
                if key.data == "tcp":
                    conn, addr = key.fileobj.accept()
                    data = conn.recv(1024).decode()
                    print(f"Recebido pacote TCP de {addr}: {data}")
                    # Procura pela linha de requisição GET
                    for line in data.splitlines():
                        if line.startswith('GET'):
                            temp, humidity, rainin = process_get_line(line)
                            latest_temp = temp
                            latest_humidity = humidity
                            latest_rainin = rainin
                            #print(f"Temperatura: {temp} °F, Umidade: {humidity} %, Precipitação: {rainin} mm")
                    conn.close()
    except KeyboardInterrupt:
        print("Encerrando servidor...")
    finally:
        sel.close()


if __name__ == "__main__":
    # Cria threads para rodar as funções em paralelo
    packet_thread = threading.Thread(target=identify_packet)

    # Inicia as threads
    packet_thread.start()

    while True:
        print(latest_temp,latest_humidity,latest_rainin)
        time.sleep(5)

    # Aguarda as threads terminarem (tecnicamente não terminarão até o encerramento do programa)
    packet_thread.join()



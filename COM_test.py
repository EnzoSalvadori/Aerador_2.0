import serial

# Defina a porta COM que você deseja testar
porta_com = 'COM1'  # Altere para a porta COM que você deseja testar

try:
    # Tenta abrir a porta serial
    ser = serial.Serial(porta_com)
    if ser.is_open:
        print(f"A porta {porta_com} está aberta e pronta para comunicação.")
        ser.close()  # Fecha a porta serial
    else:
        print(f"Não foi possível abrir a porta {porta_com}.")
except serial.SerialException as e:
    print(f"Ocorreu um erro ao abrir a porta {porta_com}: {e}")

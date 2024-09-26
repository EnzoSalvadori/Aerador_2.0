import sqlite3
import rsa

banco  = sqlite3.connect("config.db")
cursor = banco.cursor()

# Carrega a chave pública
with open("public_key.pem", "rb") as public_key_file:
    public_key_data = public_key_file.read()
    public_key = rsa.PublicKey.load_pkcs1(public_key_data)


num_silos = 6

cursor.execute("CREATE TABLE  silos (Nome text, Estado text, Produto text, Min float, Max float, TempMax float)")
for i in range(num_silos):
    nome_silo = f"Silo_{i+1}"

    cursor.execute("INSERT INTO silos VALUES (?, ?, ?, ?, ?, ?)", (nome_silo,'ligado','Vazio',13.0,14.0,20.0))

    sql = f'''CREATE TABLE  tempo_uso_{i} ( data DATETIME, liga_desliga int)'''
    cursor.execute(sql)

cursor.execute("CREATE TABLE  opts (Nsilos int, COM text, API_EST text)")
cursor.execute("INSERT INTO opts VALUES (?, ?, ?)", (num_silos,'/dev/ttyS0','https://api.weather.com/v2/pws/observations/current?apiKey=e1f10a1e78da46f5b10a1e78da96f525&stationId=IGUARA60&numericPrecision=decimal&format=json&units=m'))

# Criptografa a mensagem usando a chave pública
senha_criptografada = rsa.encrypt(b'S@fr@2024', public_key)

cursor.execute("CREATE TABLE login (User text, Password text)")
cursor.execute("INSERT INTO login VALUES (?, ?)", ('Admin',senha_criptografada))

banco.commit()

cursor.execute("SELECT * FROM silos")
print(cursor.fetchall())

cursor.execute("SELECT * FROM opts")
print(cursor.fetchall())

cursor.execute("SELECT * FROM login")
print(cursor.fetchall())
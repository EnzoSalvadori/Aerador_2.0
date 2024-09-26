import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime
from matplotlib.dates import DateFormatter

# Conectar ao banco de dados SQLite
conn = sqlite3.connect('config.db')
cursor = conn.cursor()

# Nome da tabela
nome_tabela = 'tempo_uso_0'

# Consulta SQL para obter dados da tabela
consulta_sql = f'SELECT data, liga_desliga FROM {nome_tabela}'

# Executar a consulta
cursor.execute(consulta_sql)

# Obter resultados
resultados = cursor.fetchall()

# Fechar a conexão com o banco de dados
conn.close()

# Descompactar dados e converter strings para objetos de data e hora
datas, liga_desliga = zip(*resultados)
datas = [datetime.strptime(data.split('.')[0], '%Y-%m-%d %H:%M:%S') for data in datas]

# Ordenar os dados com base na data
sorted_indices = sorted(range(len(datas)), key=lambda k: datas[k])
datas_sorted = [datas[i] for i in sorted_indices]
liga_desliga_sorted = [liga_desliga[i] for i in sorted_indices]

# Criar gráfico com pontos e linha vermelha
plt.scatter(datas_sorted, liga_desliga_sorted, marker='o')
plt.plot(datas_sorted, liga_desliga_sorted, color='red', linestyle='-', marker='o')

# Configurar o formato do eixo x
plt.gca().xaxis.set_major_formatter(DateFormatter('%Y-%m-%d %H:%M:%S'))

# Rotacionar rótulos do eixo x para melhor legibilidade, se necessário
plt.xticks(rotation=45)

# Adicionar rótulos e título
plt.xlabel('Data e Hora')
plt.ylabel('Liga/Desliga')
plt.title(f'Pontos e Linha Crescente da tabela {nome_tabela}')

# Exibir o gráfico
plt.show()

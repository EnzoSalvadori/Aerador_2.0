from flask import Flask, render_template, request
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

DATABASE_NAME = 'config.db'

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

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
    conn.close()

    # Preparar dados para o gráfico
    x_values = [datetime.strptime(entry[0], '%Y-%m-%d %H:%M:%S.%f') for entry in data]
    y_values = [entry[1] for entry in data]

    # Calcular a diferença em horas entre os pontos consecutivos onde o valor é 1 (ligado)
    total_time_on = datetime.strptime('00:00:00', '%H:%M:%S')
    for i in range(len(x_values) - 1):
        if y_values[i] == 1:
            time_difference = x_values[i + 1] - x_values[i]
            total_time_on += time_difference

    total_time_on_formatted = total_time_on.strftime('%H:%M:%S')

    print(total_time_on_formatted)

    # Convertendo para o formato de hora, minuto e segundo para o grafico
    formatted_x_values = [entry.strftime('%H:%M:%S') for entry in x_values]

    return render_template('grafico.html', x_values=formatted_x_values, y_values=y_values, selected_day=selected_day,selected_silo=selected_silo,Nsilos=4)

if __name__ == '__main__':
    app.run(debug=True)

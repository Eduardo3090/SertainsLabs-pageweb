from flask import Flask, render_template, request, redirect, url_for  # NUEVO: request, redirect, url_for
from datetime import datetime  # NUEVO
from sheets import guardar_contacto  # NUEVO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu-clave-secreta-cambia-esto-en-produccion'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/servicios')
def servicios():
    return render_template('servicios.html')

@app.route('/equipo')
def equipo():
    integrantes = [
        {
            'nombre': 'Felipe Pérez', 
            'cargo': 'Administrador', 
            'responsabilidades': [
                'Gestión de proyectos',
                'Desarrollo full-stack',
                'Infraestructura cloud',
                'Seguridad y respaldos',
                'Atención a clientes',
                'Planificación estratégica'
            ]
        },
        {
            'nombre': 'Eduardo Salazar', 
            'cargo': 'Gerente General', 
            'responsabilidades': [
                'Estrategia comercial',
                'Desarrollo backend',
                'Relaciones institucionales',
                'Innovación tecnológica',
                'Cumplimiento de plazos',
                'Gestión financiera'
            ]
        }
    ]
    return render_template('equipo.html', integrantes=integrantes)

@app.route('/contacto')
def contacto():
    return render_template('contacto.html')

@app.route('/agendar', methods=['POST'])  # NUEVO: toda esta función
def agendar():
    nombre = request.form.get('nombre', '').strip()
    email = request.form.get('email', '').strip()
    mensaje = request.form.get('mensaje', '').strip()

    if not nombre or not email:
        return redirect(url_for('index'))

    fecha = datetime.now().strftime('%Y-%m-%d %H:%M')

    try:
        guardar_contacto(nombre, email, mensaje, fecha)
    except Exception as e:
        print(f"Error guardando en Sheets: {e}")
        return redirect(url_for('index'))

    return redirect(url_for('gracias'))

@app.route('/gracias')
def gracias():
    return render_template('gracias.html')

if __name__ == '__main__':
    app.run(debug=True)

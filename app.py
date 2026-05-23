from flask import Flask, render_template

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

@app.route('/gracias')
def gracias():
    return render_template('gracias.html')

if __name__ == '__main__':
    app.run(debug=True)
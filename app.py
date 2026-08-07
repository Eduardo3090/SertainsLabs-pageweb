from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from sheets import guardar_contacto
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu-clave-secreta-cambia-esto-en-produccion'


def enviar_correo_contacto(nombre, email_cliente, empresa, servicio, mensaje):
    remitente = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASSWORD')
    destinatario = os.environ.get('EMAIL_TO')

    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = f'Nueva solicitud de reunión - {nombre}'
    msg['Reply-To'] = email_cliente

    cuerpo = f"""Nueva solicitud desde sertainslabs.cl

Nombre completo: {nombre}
Correo electrónico: {email_cliente}
Empresa/Emprendimiento: {empresa or 'No especificado'}
Servicio de interés: {servicio or 'No especificado'}

Mensaje del cliente:
{mensaje}
"""
    msg.attach(MIMEText(cuerpo, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as server:
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())
        return True
    except Exception as e:
        print(f"Error enviando correo: {e}")
        return False


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


@app.route('/agendar', methods=['POST'])
def agendar():
    nombre = request.form.get('nombre', '').strip()
    email = request.form.get('email', '').strip()
    empresa = request.form.get('empresa', '').strip()
    servicio = request.form.get('servicio', '').strip()
    mensaje = request.form.get('mensaje', '').strip()

    if not nombre or not email:
        return redirect(url_for('index'))

    fecha = datetime.now().strftime('%Y-%m-%d %H:%M')

    try:
        guardar_contacto(nombre, email, mensaje, fecha)
    except Exception as e:
        print(f"Error guardando en Sheets: {e}")

    try:
        enviar_correo_contacto(nombre, email, empresa, servicio, mensaje)
    except Exception as e:
        print(f"Error enviando correo: {e}")

    return redirect(url_for('gracias'))


@app.route('/gracias')
def gracias():
    return render_template('gracias.html')


if __name__ == '__main__':
    app.run(debug=True)

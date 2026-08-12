from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from sheets import guardar_contacto
import smtplib
import os
import resend
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu-clave-secreta-cambia-esto-en-produccion'


resend.api_key = os.environ.get('RESEND_API_KEY')

def enviar_correo_contacto(nombre, email_cliente, empresa, servicio, mensaje):
    cuerpo_html = f"""
    <h2>Nueva solicitud desde sertainslabs.cl</h2>
    <p><strong>Nombre completo:</strong> {nombre}</p>
    <p><strong>Correo electrónico:</strong> {email_cliente}</p>
    <p><strong>Empresa/Emprendimiento:</strong> {empresa or 'No especificado'}</p>
    <p><strong>Servicio de interés:</strong> {servicio or 'No especificado'}</p>
    <p><strong>Mensaje del cliente:</strong></p>
    <p>{mensaje}</p>
    """
    try:
        resend.Emails.send({
            "from": "Sertains Labs <onboarding@resend.dev>",
            "to": ["sertainslabs@gmail.com"],
            "reply_to": email_cliente,
            "subject": f"Nueva solicitud de reunión - {nombre}",
            "html": cuerpo_html,
        })
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

@app.route('/portafolio')
def portafolio():
    proyectos = [
        {
            'nombre': 'Megadiseños',
            'descripcion': 'Sitio corporativo para imprenta en Copiapó, con catálogo de productos, cotizador integrado y SEO local orientado a "imprenta en Copiapó".',
            'tags': ['Flask', 'SEO local', 'WhatsApp API'],
            'imagen': 'https://megadise-os.onrender.com/static/proyecto-gigantografia-estatal.jpg',
            'es_logo': False,
            'url': 'https://megadise-os.onrender.com/'
        },
        {
            'nombre': 'M&J Consultores Estratégicos',
            'descripcion': 'Sitio institucional para consultora de prevención de riesgos, administración y logística, con captación de leads y roadmap de nuevas funciones.',
            'tags': ['Flask', 'Landing institucional', 'Captación de leads'],
            'imagen': 'https://mjy-consultores.onrender.com/static/logo.png',
            'es_logo': True,
            'url': 'https://mjy-consultores.onrender.com/'
        }
    ]
    return render_template('portafolio.html', proyectos=proyectos)

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, g, send_file, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.urls import url_parse
import os
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from werkzeug.utils import secure_filename
from sqlalchemy import func
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from functools import wraps
from io import BytesIO
import paypalrestsdk
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
import qrcode
from PIL import Image
import base64

# Cargar variables de entorno
load_dotenv()

# Configurar PayPal
PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'sandbox')
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', 'tu_client_id_aqui')
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET', 'tu_client_secret_aqui')
PAYPAL_SIMULATION = os.getenv('PAYPAL_SIMULATION', 'true').lower() == 'true'

paypalrestsdk.configure({
    "mode": PAYPAL_MODE,
    "client_id": PAYPAL_CLIENT_ID,
    "client_secret": PAYPAL_CLIENT_SECRET
})

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'tu_clave_secreta_aqui')
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}/{os.getenv('DB_NAME', 'sistema_electronicos')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = './images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

# Asegurarse de que la carpeta de imágenes existe
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'warning'

# Modelos
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    tipo_usuario = db.Column(db.Enum('admin', 'vendedor', 'usuario'), nullable=False, default='usuario')
    nit = db.Column(db.String(11), unique=True, nullable=True)
    direccion = db.Column(db.Text, nullable=True)
    telefono = db.Column(db.String(20), nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.Enum('activo', 'inactivo'), nullable=False, default='activo')
    
    def get_id(self):
        return str(self.id_usuario)
    
    def is_admin(self):
        return self.tipo_usuario == 'admin'
    
    def is_vendedor(self):
        return self.tipo_usuario == 'vendedor'

class Producto(db.Model):
    __tablename__ = 'productos'
    id_producto = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    id_categoria = db.Column(db.Integer, db.ForeignKey('categorias.id_categoria'), nullable=False)
    imagen = db.Column(db.String(255))
    estado = db.Column(db.String(20), default='activo')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    categoria = db.relationship('Categoria', backref=db.backref('productos', lazy=True))

class Categoria(db.Model):
    __tablename__ = 'categorias'
    id_categoria = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

class Carrito(db.Model):
    __tablename__ = 'carrito'
    id_carrito = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario', ondelete='CASCADE'), nullable=False)
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto', ondelete='CASCADE'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    fecha_agregado = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    usuario = db.relationship('Usuario', backref=db.backref('carrito', lazy=True))
    producto = db.relationship('Producto', backref=db.backref('carrito', lazy=True))
    
    __table_args__ = (
        db.UniqueConstraint('id_usuario', 'id_producto', name='unique_producto_usuario'),
    )

class Pedido(db.Model):
    __tablename__ = 'pedidos'
    
    id_pedido = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario', ondelete='CASCADE'), nullable=False)
    numero_factura = db.Column(db.String(20), unique=True, nullable=False)
    fecha_pedido = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, nullable=True)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    iva = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.Enum('pendiente', 'en_proceso', 'enviado', 'entregado', 'cancelado'), default='pendiente')
    direccion_envio = db.Column(db.String(200), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    metodo_pago = db.Column(db.String(50), nullable=True)
    paypal_payment_id = db.Column(db.String(255))
    
    # Relaciones
    usuario = db.relationship('Usuario', backref=db.backref('pedidos', lazy=True))
    detalles = db.relationship('DetallePedido', backref='pedido', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Pedido {self.id_pedido}>'

class DetallePedido(db.Model):
    __tablename__ = 'detalles_pedido'
    
    id_detalle = db.Column(db.Integer, primary_key=True)
    id_pedido = db.Column(db.Integer, db.ForeignKey('pedidos.id_pedido', ondelete='CASCADE'), nullable=False)
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto', ondelete='CASCADE'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Relaciones
    producto = db.relationship('Producto', backref=db.backref('detalles_pedido', lazy=True))

class Factura(db.Model):
    __tablename__ = 'facturas'
    
    id_factura = db.Column(db.Integer, primary_key=True)
    id_pedido = db.Column(db.Integer, db.ForeignKey('pedidos.id_pedido', ondelete='CASCADE'), nullable=False)
    numero_factura = db.Column(db.String(20), unique=True, nullable=False)
    voucher_number = db.Column(db.String(20), unique=True, nullable=False)
    fecha_emision = db.Column(db.DateTime, default=datetime.utcnow)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    iva = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.Enum('emitida', 'anulada'), default='emitida')
    pdf_path = db.Column(db.String(255))
    
    # Relaciones
    pedido = db.relationship('Pedido', backref=db.backref('factura', uselist=False))
    estados = db.relationship('EstadoFactura', backref='factura', lazy=True)

class EstadoFactura(db.Model):
    __tablename__ = 'estados_factura'
    
    id_estado = db.Column(db.Integer, primary_key=True)
    id_factura = db.Column(db.Integer, db.ForeignKey('facturas.id_factura', ondelete='CASCADE'), nullable=False)
    estado = db.Column(db.Enum('pendiente', 'emitida', 'anulada', 'reimpresa'), nullable=False)
    fecha_cambio = db.Column(db.DateTime, default=datetime.utcnow)
    id_admin = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario', ondelete='SET NULL'))
    observacion = db.Column(db.Text)
    
    # Relaciones
    admin = db.relationship('Usuario', backref=db.backref('estados_factura', lazy=True))

# Funciones de validación
def validar_nit(nit):
    if not nit or not nit.isdigit() or len(nit) != 11:
        return False
    return True

def validar_email(email):
    if not email or '@' not in email:
        return False
    return True

def validar_telefono(telefono):
    if not telefono or not telefono.isdigit() or len(telefono) < 7:
        return False
    return True

def validar_precio(precio):
    try:
        precio_float = float(precio)
        return precio_float > 0
    except:
        return False

def validar_stock(stock):
    try:
        stock_int = int(stock)
        return stock_int >= 0
    except:
        return False

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Rutas principales
@app.route('/')
def index():
    productos = Producto.query.filter_by(estado='activo').all()
    categorias = Categoria.query.all()
    return render_template('index.html', productos=productos, categorias=categorias)

@app.route('/buscar_productos')
def buscar_productos():
    query = request.args.get('q', '')
    if query:
        productos = Producto.query.filter(
            (Producto.nombre.ilike(f'%{query}%')) |
            (Producto.descripcion.ilike(f'%{query}%'))
        ).filter_by(estado='activo').all()
    else:
        productos = Producto.query.filter_by(estado='activo').all()
    return render_template('index.html', productos=productos, categorias=Categoria.query.all(), query=query)

@app.route('/categoria/<int:id>')
def categoria(id):
    categoria = Categoria.query.get_or_404(id)
    productos = Producto.query.filter_by(id_categoria=id, estado='activo').all()
    return render_template('index.html', productos=productos, categorias=Categoria.query.all(), categoria_actual=categoria)

@app.route('/producto/<int:id>')
def producto(id):
    producto = Producto.query.get_or_404(id)
    return render_template('producto.html', producto=producto)

@app.route('/servicios_mantenimiento')
def servicios_mantenimiento():
    return render_template('servicios_mantenimiento.html')

@app.route('/agregar_servicio_carrito', methods=['POST'])
@login_required
def agregar_servicio_carrito():
    try:
        id_servicio = int(request.form.get('id_servicio'))
        nombre_servicio = request.form.get('nombre_servicio')
        precio_servicio = float(request.form.get('precio_servicio'))
        tipo = request.form.get('tipo')
        
        # Crear un producto temporal para el servicio
        servicio_producto = {
            'id_producto': f'servicio_{id_servicio}',
            'nombre': nombre_servicio,
            'precio': precio_servicio,
            'tipo': tipo,
            'descripcion': f'Servicio de mantenimiento: {nombre_servicio}',
            'imagen': None
        }
        
        # Agregar al carrito (usando la funcionalidad existente)
        item_carrito = Carrito(
            id_usuario=current_user.id_usuario,
            id_producto=id_servicio,  # Usar el ID del servicio
            cantidad=1
        )
        
        # Guardar información adicional del servicio en la sesión
        if 'servicios_carrito' not in session:
            session['servicios_carrito'] = {}
        
        session['servicios_carrito'][str(id_servicio)] = {
            'nombre': nombre_servicio,
            'precio': precio_servicio,
            'tipo': tipo
        }
        
        db.session.add(item_carrito)
        db.session.commit()
        
        flash(f'Servicio "{nombre_servicio}" agregado al carrito exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al agregar el servicio al carrito', 'error')
        print(f"Error: {str(e)}")
    
    return redirect(url_for('servicios_mantenimiento'))

@app.route('/eliminar_servicio_carrito/<id_servicio>')
@login_required
def eliminar_servicio_carrito(id_servicio):
    try:
        # Eliminar servicio de la sesión
        if 'servicios_carrito' in session and id_servicio in session['servicios_carrito']:
            servicio_nombre = session['servicios_carrito'][id_servicio]['nombre']
            del session['servicios_carrito'][id_servicio]
            session.modified = True
            flash(f'Servicio "{servicio_nombre}" eliminado del carrito', 'success')
        else:
            flash('Servicio no encontrado en el carrito', 'error')
    except Exception as e:
        flash('Error al eliminar el servicio del carrito', 'error')
        print(f"Error: {str(e)}")
    
    return redirect(url_for('carrito'))

@app.before_request
def before_request():
    if current_user.is_authenticated:
        # Contar productos en el carrito
        carrito_count = Carrito.query.filter_by(id_usuario=current_user.id_usuario).count()
        
        # Contar servicios en el carrito
        servicios_count = len(session.get('servicios_carrito', {}))
        
        # Total de items en el carrito
        g.carrito_count = carrito_count + servicios_count
    else:
        g.carrito_count = 0

@app.route('/carrito/agregar', methods=['POST'])
@login_required
def agregar_al_carrito():
    try:
        id_producto = int(request.form.get('id_producto'))
        cantidad = int(request.form.get('cantidad', 1))
        
        if cantidad <= 0:
            flash('La cantidad debe ser mayor a 0', 'error')
            return redirect(url_for('producto', id=id_producto))
        
        producto = Producto.query.get_or_404(id_producto)
        
        if producto.stock < cantidad:
            flash('No hay suficiente stock disponible', 'error')
            return redirect(url_for('producto', id=id_producto))
        
        # Verificar si el producto ya está en el carrito
        item_carrito = Carrito.query.filter_by(
            id_usuario=current_user.id_usuario,
            id_producto=id_producto
        ).first()
        
        if item_carrito:
            # Actualizar cantidad si ya existe
            nueva_cantidad = item_carrito.cantidad + cantidad
            if nueva_cantidad > producto.stock:
                flash('No hay suficiente stock disponible', 'error')
                return redirect(url_for('producto', id=id_producto))
            item_carrito.cantidad = nueva_cantidad
        else:
            # Crear nuevo item en el carrito
            item_carrito = Carrito(
                id_usuario=current_user.id_usuario,
                id_producto=id_producto,
                cantidad=cantidad
            )
            db.session.add(item_carrito)
        
        db.session.commit()
        flash('Producto agregado al carrito exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al agregar al carrito', 'error')
        print(f"Error: {str(e)}")  # Para debugging
    
    return redirect(url_for('carrito'))

@app.route('/carrito')
@login_required
def carrito():
    try:
        items_carrito = Carrito.query.filter_by(id_usuario=current_user.id_usuario).all()
        
        # Obtener servicios del carrito desde la sesión
        servicios_carrito = session.get('servicios_carrito', {})
        
        # Calcular total de productos
        total_productos = sum(Decimal(str(item.producto.precio)) * item.cantidad for item in items_carrito)
        
        # Calcular total de servicios
        total_servicios = sum(Decimal(str(servicio['precio'])) for servicio in servicios_carrito.values())
        
        # Total general
        total = total_productos + total_servicios
        
        return render_template('carrito.html', 
                             items=items_carrito, 
                             servicios=servicios_carrito,
                             total=total,
                             total_productos=total_productos,
                             total_servicios=total_servicios)
    except Exception as e:
        print(f"Error en carrito: {str(e)}")  # Para debugging
        flash('Error al cargar el carrito', 'error')
        return redirect(url_for('index'))

@app.route('/carrito/actualizar', methods=['POST'])
@login_required
def actualizar_carrito():
    try:
        id_carrito = int(request.form.get('id_carrito'))
        cantidad = int(request.form.get('cantidad', 0))
        
        if cantidad < 0:
            flash('La cantidad debe ser mayor o igual a 0', 'error')
            return redirect(url_for('carrito'))
        
        item_carrito = Carrito.query.get_or_404(id_carrito)
        
        # Verificar que el item pertenece al usuario actual
        if item_carrito.id_usuario != current_user.id_usuario:
            flash('No tienes permiso para modificar este item', 'error')
            return redirect(url_for('carrito'))
        
        if cantidad == 0:
            # Eliminar item si la cantidad es 0
            db.session.delete(item_carrito)
        else:
            # Verificar stock
            if cantidad > item_carrito.producto.stock:
                flash('No hay suficiente stock disponible', 'error')
                return redirect(url_for('carrito'))
            item_carrito.cantidad = cantidad
        
        db.session.commit()
        flash('Carrito actualizado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al actualizar el carrito', 'error')
        print(f"Error: {str(e)}")  # Para debugging
    
    return redirect(url_for('carrito'))

@app.route('/carrito/eliminar/<int:id>')
@login_required
def eliminar_del_carrito(id):
    try:
        item_carrito = Carrito.query.get_or_404(id)
        
        # Verificar que el item pertenece al usuario actual
        if item_carrito.id_usuario != current_user.id_usuario:
            flash('No tienes permiso para eliminar este item', 'error')
            return redirect(url_for('carrito'))
        
        db.session.delete(item_carrito)
        db.session.commit()
        flash('Producto eliminado del carrito exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar del carrito', 'error')
        print(f"Error: {str(e)}")  # Para debugging
    
    return redirect(url_for('carrito'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        direccion = request.form.get('direccion')
        metodo_pago = request.form.get('metodo_pago')
        
        items = Carrito.query.filter_by(id_usuario=current_user.id_usuario).all()
        servicios_carrito = session.get('servicios_carrito', {})
        
        if not items and not servicios_carrito:
            flash('El carrito está vacío')
            return redirect(url_for('carrito'))
        
        # Calcular total de productos
        total_productos = sum(Decimal(str(item.producto.precio)) * item.cantidad for item in items) if items else Decimal('0')
        
        # Calcular total de servicios
        total_servicios = sum(Decimal(str(servicio['precio'])) for servicio in servicios_carrito.values()) if servicios_carrito else Decimal('0')
        
        total = total_productos + total_servicios
        
        pedido = Pedido(
            id_usuario=current_user.id_usuario,
            total=total,
            direccion_envio=direccion,
            telefono=current_user.telefono,
            estado='pendiente',
            metodo_pago=metodo_pago,
            fecha_actualizacion=datetime.utcnow()
        )
        db.session.add(pedido)
        db.session.flush()
        
        for item in items:
            detalle = DetallePedido(
                id_pedido=pedido.id_pedido,
                id_producto=item.id_producto,
                cantidad=item.cantidad,
                precio_unitario=item.producto.precio,
                subtotal=item.producto.precio * item.cantidad
            )
            db.session.add(detalle)
            
            producto = item.producto
            producto.stock -= item.cantidad
            if producto.stock < 0:
                db.session.rollback()
                flash('Stock insuficiente para algunos productos')
                return redirect(url_for('carrito'))
        
        # Limpiar carrito de productos
        Carrito.query.filter_by(id_usuario=current_user.id_usuario).delete()
        
        # Limpiar carrito de servicios de la sesión
        if 'servicios_carrito' in session:
            del session['servicios_carrito']
            session.modified = True
        
        db.session.commit()
        
        flash('Pedido realizado con éxito. Los servicios de mantenimiento se agendarán pronto.')
        return redirect(url_for('user_dashboard'))
    
    items = Carrito.query.filter_by(id_usuario=current_user.id_usuario).all()
    servicios_carrito = session.get('servicios_carrito', {})
    
    # Calcular totales
    total_productos = sum(Decimal(str(item.producto.precio)) * item.cantidad for item in items) if items else Decimal('0')
    total_servicios = sum(Decimal(str(servicio['precio'])) for servicio in servicios_carrito.values()) if servicios_carrito else Decimal('0')
    total = total_productos + total_servicios
    
    return render_template('checkout.html', 
                         items=items, 
                         servicios=servicios_carrito,
                         total=total,
                         total_productos=total_productos,
                         total_servicios=total_servicios)

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        password = request.form.get('password')
        nit = request.form.get('nit')
        direccion = request.form.get('direccion')
        telefono = request.form.get('telefono')
        
        # Validaciones
        if not nombre or len(nombre.strip()) == 0:
            flash('El nombre es requerido', 'error')
            return redirect(url_for('registro'))
        
        if not validar_email(email):
            flash('Email inválido', 'error')
            return redirect(url_for('registro'))
        
        if not validar_nit(nit):
            flash('NIT inválido. Debe contener 11 dígitos', 'error')
            return redirect(url_for('registro'))
        
        if not validar_telefono(telefono):
            flash('Teléfono inválido', 'error')
            return redirect(url_for('registro'))
        
        # Verificar duplicados
        if Usuario.query.filter_by(email=email).first():
            flash('Este email ya está registrado', 'error')
            return redirect(url_for('registro'))
        
        if Usuario.query.filter_by(nit=nit).first():
            flash('Este NIT ya está registrado', 'error')
            return redirect(url_for('registro'))
        
        # Crear usuario
        nuevo_usuario = Usuario(
            nombre=nombre,
            email=email,
            password=generate_password_hash(password, method='pbkdf2:sha256'),
            nit=nit,
            direccion=direccion,
            telefono=telefono,
            tipo_usuario='usuario'
        )
        
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash('¡Registro exitoso! Por favor inicia sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Error al registrar usuario.', 'error')
            print(f"Error: {str(e)}")
    
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = Usuario.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            if user.estado == 'inactivo':
                flash('Tu cuenta está desactivada. Por favor, contacta al administrador.', 'danger')
                return redirect(url_for('login'))
            
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('dashboard')
            return redirect(next_page)
        else:
            flash('Email o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('No tienes permiso para acceder a esta página.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('user_dashboard'))

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    try:
        # Obtener estadísticas
        total_ventas = db.session.query(func.sum(Pedido.total)).filter(Pedido.estado != 'cancelado').scalar() or 0
        pedidos_pendientes = Pedido.query.filter_by(estado='pendiente').count()
        total_usuarios = Usuario.query.filter_by(tipo_usuario='usuario').count()
        total_productos = Producto.query.count()
        
        # Obtener pedidos pendientes
        pedidos = Pedido.query.filter_by(estado='pendiente').order_by(Pedido.fecha_pedido.desc()).limit(5).all()
        
        # Obtener ventas por mes
        ventas_mes = db.session.query(
            func.date_format(Pedido.fecha_pedido, '%Y-%m').label('mes'),
            func.sum(Pedido.total).label('total')
        ).filter(
            Pedido.estado != 'cancelado'
        ).group_by('mes').order_by('mes').limit(6).all()
        
        # Obtener productos más vendidos
        productos_mas_vendidos = db.session.query(
            Producto.nombre,
            func.sum(DetallePedido.cantidad).label('total_vendido')
        ).join(DetallePedido).group_by(Producto.id_producto).order_by(
            func.sum(DetallePedido.cantidad).desc()
        ).limit(5).all()
        
        return render_template('admin/dashboard.html',
                             total_ventas=total_ventas,
                             pedidos_pendientes=pedidos_pendientes,
                             total_usuarios=total_usuarios,
                             total_productos=total_productos,
                             pedidos=pedidos,
                             ventas_mes=ventas_mes,
                             productos_mas_vendidos=productos_mas_vendidos)
    except Exception as e:
        flash('Error al cargar el dashboard', 'danger')
        print(f"Error en dashboard: {str(e)}")
        return redirect(url_for('index'))

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    try:
        # Obtener los últimos pedidos del usuario
        pedidos = Pedido.query.filter_by(id_usuario=current_user.id_usuario)\
            .order_by(Pedido.fecha_pedido.desc())\
            .limit(5).all()
        
        return render_template('user/dashboard.html', pedidos=pedidos)
    except Exception as e:
        flash('Error al cargar el dashboard', 'danger')
        print(f"Error en dashboard de usuario: {str(e)}")
        return redirect(url_for('index'))

@app.route('/admin/pedidos')
@login_required
@admin_required
def admin_pedidos():
    # Obtener parámetros de filtrado
    estado = request.args.get('estado', '')
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    cliente = request.args.get('cliente', '')
    page = request.args.get('page', 1, type=int)
    
    # Construir la consulta base
    query = Pedido.query
    
    # Aplicar filtros
    if estado:
        query = query.filter(Pedido.estado == estado)
    if fecha_desde:
        query = query.filter(Pedido.fecha_pedido >= datetime.strptime(fecha_desde, '%Y-%m-%d'))
    if fecha_hasta:
        query = query.filter(Pedido.fecha_pedido <= datetime.strptime(fecha_hasta, '%Y-%m-%d'))
    if cliente:
        query = query.join(Usuario).filter(Usuario.nombre.ilike(f'%{cliente}%'))
    
    # Ordenar por fecha descendente
    query = query.order_by(Pedido.fecha_pedido.desc())
    
    # Paginación
    pedidos = query.paginate(page=page, per_page=10)
    
    return render_template('admin/pedidos.html', 
                         pedidos=pedidos,
                         estado=estado,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta,
                         cliente=cliente)

@app.route('/admin/facturas')
@login_required
@admin_required
def admin_facturas():
    # Obtener parámetros de filtrado
    estado = request.args.get('estado', '')
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    cliente = request.args.get('cliente', '')
    page = request.args.get('page', 1, type=int)
    
    # Construir la consulta base
    query = Factura.query
    
    # Aplicar filtros
    if estado:
        query = query.filter(Factura.estado == estado)
    if fecha_desde:
        query = query.filter(Factura.fecha_emision >= datetime.strptime(fecha_desde, '%Y-%m-%d'))
    if fecha_hasta:
        query = query.filter(Factura.fecha_emision <= datetime.strptime(fecha_hasta, '%Y-%m-%d'))
    if cliente:
        query = query.join(Pedido).join(Usuario).filter(Usuario.nombre.ilike(f'%{cliente}%'))
    
    # Ordenar por fecha descendente
    query = query.order_by(Factura.fecha_emision.desc())
    
    # Paginación
    pagination = query.paginate(page=page, per_page=10)
    
    return render_template('admin/facturas.html', 
                         facturas=pagination.items,
                         pagination=pagination,
                         estado=estado,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta,
                         cliente=cliente)

@app.route('/admin/usuarios')
@login_required
@admin_required
def admin_usuarios():
    # Obtener parámetros de filtrado
    nombre = request.args.get('nombre', '')
    email = request.args.get('email', '')
    page = request.args.get('page', 1, type=int)
    
    # Construir la consulta base
    query = Usuario.query
    
    # Aplicar filtros
    if nombre:
        query = query.filter(Usuario.nombre.ilike(f'%{nombre}%'))
    if email:
        query = query.filter(Usuario.email.ilike(f'%{email}%'))
    
    # Ordenar por nombre
    query = query.order_by(Usuario.nombre)
    
    # Paginación
    usuarios = query.paginate(page=page, per_page=10)
    
    return render_template('admin/usuarios.html', 
                         usuarios=usuarios,
                         nombre=nombre,
                         email=email)

@app.route('/admin/productos')
@login_required
@admin_required
def admin_productos():
    # Obtener parámetros de filtrado
    nombre = request.args.get('nombre', '')
    categoria_id = request.args.get('categoria', '', type=int)
    
    # Construir la consulta base
    query = Producto.query
    
    # Aplicar filtros
    if nombre:
        query = query.filter(Producto.nombre.ilike(f'%{nombre}%'))
    if categoria_id:
        query = query.filter(Producto.id_categoria == categoria_id)
    
    # Ordenar por nombre
    query = query.order_by(Producto.nombre)
    
    # Obtener todos los productos que coinciden con los filtros
    productos = query.all()

    # Obtener categorías para el filtro y la visualización
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    
    # Crear un diccionario para mapear IDs de categoría a nombres para la visualización
    categorias_map = {cat.id_categoria: cat.nombre for cat in categorias}
    
    # Agregar el nombre de la categoría a cada producto para la visualización
    productos_display = []
    for producto in productos:
        producto_dict = {
            'id_producto': producto.id_producto,
            'nombre': producto.nombre,
            'descripcion': producto.descripcion,
            'precio': producto.precio,
            'stock': producto.stock,
            'imagen': producto.imagen,
            'nombre_categoria': categorias_map.get(producto.id_categoria, 'Sin categoría')
        }
        productos_display.append(producto_dict)
        
    return render_template('admin/productos.html', 
                           productos=productos_display,
                           categorias=categorias,
                           nombre=nombre,
                           categoria_id=categoria_id)

@app.route('/admin/productos/agregar', methods=['GET', 'POST'])
@login_required
@admin_required
def agregar_producto():
    if not current_user.is_admin:
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('index'))

    from werkzeug.utils import secure_filename
    import os

    categorias = Categoria.query.order_by(Categoria.nombre).all()
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        precio = request.form.get('precio', type=float)
        stock = request.form.get('stock', type=int)
        id_categoria = request.form.get('categoria', type=int)
        imagen = request.files.get('imagen')
        imagen_filename = None
        if imagen and imagen.filename:
            filename = secure_filename(imagen.filename)
            imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # No es necesario crear subdirectorios si UPLOAD_FOLDER ya apunta a la raíz de las imágenes
            # os.makedirs(os.path.dirname(imagen_path), exist_ok=True) # Esta línea se eliminará o comentará
            imagen.save(imagen_path)
            imagen_filename = filename # Guardar solo el nombre del archivo
        try:
            producto = Producto(
                nombre=nombre,
                descripcion=descripcion,
                precio=precio,
                stock=stock,
                id_categoria=id_categoria,
                imagen=imagen_filename
            )
            db.session.add(producto)
            db.session.commit()
            flash('Producto agregado exitosamente', 'success')
            return redirect(url_for('admin_productos'))
        except Exception as e:
            db.session.rollback()
            flash('Error al agregar el producto', 'danger')
            print(f"Error: {str(e)}")
    return render_template('admin/agregar_producto.html', categorias=categorias)

@app.route('/admin/productos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_producto(id):
    if not current_user.is_admin:
        flash('No tienes permiso para acceder a esta página.', 'danger')
        return redirect(url_for('index'))
    
    producto = Producto.query.get_or_404(id)
    categorias = Categoria.query.all()
    
    # Limpiar la ruta de la imagen para display y operaciones de eliminación
    # Asegura que solo el nombre del archivo se use, independientemente de cómo se haya guardado previamente
    if producto.imagen and ('/' in producto.imagen or '\\' in producto.imagen):
        producto.imagen = os.path.basename(producto.imagen)
    
    if request.method == 'POST':
        try:
            producto.nombre = request.form['nombre']
            producto.descripcion = request.form['descripcion']
            producto.precio = float(request.form['precio'])
            producto.stock = int(request.form['stock'])
            producto.id_categoria = int(request.form['categoria'])
            
            # Manejar la imagen si se subió una nueva
            if 'imagen' in request.files:
                imagen = request.files['imagen']
                if imagen and imagen.filename:
                    # Eliminar imagen anterior si existe
                    if producto.imagen: # Verificar si un nombre de archivo existe después de la limpieza
                        try:
                            # Construir la ruta completa para la eliminación usando UPLOAD_FOLDER y el nombre de archivo
                            old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], producto.imagen)
                            if os.path.exists(old_image_path): # Verificar si el archivo realmente existe
                                os.remove(old_image_path)
                        except Exception as e:
                            print(f"Error al eliminar imagen antigua: {e}") # Registrar el error
                    
                    # Guardar nueva imagen
                    filename = secure_filename(imagen.filename)
                    imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    producto.imagen = filename # Almacenar solo el nombre del archivo en la DB
            
            db.session.commit()
            flash('Producto actualizado exitosamente.', 'success')
            return redirect(url_for('admin_productos'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el producto: {str(e)}', 'danger')
    
    return render_template('admin/editar_producto.html', 
                         producto=producto, 
                         categorias=categorias)

@app.route('/admin/productos/eliminar/<int:id>')
@login_required
@admin_required
def eliminar_producto(id):
    if not current_user.is_admin:
        flash('No tienes permiso para realizar esta acción.', 'danger')
        return redirect(url_for('index'))
    
    producto = Producto.query.get_or_404(id)
    
    try:
        # Eliminar la imagen si existe
        if producto.imagen:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], producto.imagen))
            except:
                pass
        
        db.session.delete(producto)
        db.session.commit()
        flash('Producto eliminado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el producto: {str(e)}', 'danger')
    
    return redirect(url_for('admin_productos'))

@app.route('/actualizar_perfil', methods=['GET', 'POST'])
@login_required
def actualizar_perfil():
    if request.method == 'GET':
        return render_template('user/editar_perfil.html')
        
    try:
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        direccion = request.form.get('direccion')
        nit = request.form.get('nit')
        
        # Validaciones
        if not nombre or not email:
            flash('El nombre y el email son campos obligatorios', 'danger')
            return redirect(url_for('actualizar_perfil'))
        
        if not validar_email(email):
            flash('El formato del email no es válido', 'danger')
            return redirect(url_for('actualizar_perfil'))
        
        if telefono and not validar_telefono(telefono):
            flash('El formato del teléfono no es válido', 'danger')
            return redirect(url_for('actualizar_perfil'))
        
        if nit and not validar_nit(nit):
            flash('El formato del NIT no es válido', 'danger')
            return redirect(url_for('actualizar_perfil'))
        
        # Verificar si el email ya existe (excepto para el usuario actual)
        email_existente = Usuario.query.filter(
            Usuario.email == email,
            Usuario.id_usuario != current_user.id_usuario
        ).first()
        
        if email_existente:
            flash('El email ya está registrado por otro usuario', 'danger')
            return redirect(url_for('actualizar_perfil'))
        
        # Verificar si el NIT ya existe (excepto para el usuario actual)
        if nit:
            nit_existente = Usuario.query.filter(
                Usuario.nit == nit,
                Usuario.id_usuario != current_user.id_usuario
            ).first()
            
            if nit_existente:
                flash('El NIT ya está registrado por otro usuario', 'danger')
                return redirect(url_for('actualizar_perfil'))
        
        # Actualizar datos
        current_user.nombre = nombre
        current_user.email = email
        current_user.telefono = telefono
        current_user.direccion = direccion
        current_user.nit = nit
        
        db.session.commit()
        flash('Perfil actualizado exitosamente', 'success')
        return redirect(url_for('user_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash('Error al actualizar el perfil', 'danger')
        print(f"Error: {str(e)}")
        return redirect(url_for('actualizar_perfil'))

@app.context_processor
def inject_cart_count():
    if current_user.is_authenticated:
        count = Carrito.query.filter_by(id_usuario=current_user.id_usuario).count()
        return {'carrito_count': count}
    return {'carrito_count': 0}

@app.context_processor
def inject_categories():
    return {'categorias': Categoria.query.all()}

@app.route('/pedido/<int:id>')
@login_required
def ver_pedido(id):
    pedido = Pedido.query.get_or_404(id)
    
    # Verificar que el pedido pertenece al usuario actual o es admin
    if not current_user.is_admin() and pedido.id_usuario != current_user.id_usuario:
        flash('No tienes permiso para ver este pedido', 'error')
        return redirect(url_for('user_dashboard'))
    
    return render_template('user/detalles_pedido.html', pedido=pedido)

@app.route('/admin/pedido/<int:id>')
@login_required
@admin_required
def ver_pedido_admin(id):
    try:
        pedido = Pedido.query.get_or_404(id)
        return render_template('admin/ver_pedido.html', pedido=pedido)
    except Exception as e:
        flash('Error al cargar los detalles del pedido', 'error')
        print(f"Error: {str(e)}")  # Para debugging
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/pedido/estado/<int:id>', methods=['POST'])
@login_required
@admin_required
def actualizar_estado_pedido(id):
    try:
        pedido = Pedido.query.get_or_404(id)
        nuevo_estado = request.form.get('estado')
        
        if not nuevo_estado:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Estado no proporcionado'}), 400
            flash('Estado no proporcionado', 'danger')
            return redirect(url_for('admin_pedidos'))
        
        if nuevo_estado not in ['pendiente', 'en_proceso', 'enviado', 'entregado', 'cancelado']:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Estado no válido'}), 400
            flash('Estado no válido', 'danger')
            return redirect(url_for('admin_pedidos'))
        
        # Si se está cancelando el pedido, devolver productos al stock
        if nuevo_estado == 'cancelado' and pedido.estado != 'cancelado':
            for detalle in pedido.detalles:
                producto = detalle.producto
                producto.stock += detalle.cantidad
        
        # Si se está des-cancelando el pedido, verificar stock
        if pedido.estado == 'cancelado' and nuevo_estado != 'cancelado':
            for detalle in pedido.detalles:
                if detalle.cantidad > detalle.producto.stock:
                    mensaje = f'No hay suficiente stock de {detalle.producto.nombre}'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': mensaje}), 400
                    flash(mensaje, 'danger')
                    return redirect(url_for('admin_pedidos'))
                detalle.producto.stock -= detalle.cantidad
        
        pedido.estado = nuevo_estado
        pedido.fecha_actualizacion = datetime.utcnow()
        db.session.commit()
        
        mensaje = f'Estado del pedido actualizado a {nuevo_estado.replace("_", " ").title()}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': mensaje})
        
        flash(mensaje, 'success')
        return redirect(url_for('admin_pedidos'))
        
    except Exception as e:
        db.session.rollback()
        error_msg = f'Error al actualizar el estado del pedido: {str(e)}'
        print(error_msg)  # Para debugging
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        
        flash(error_msg, 'danger')
        return redirect(url_for('admin_pedidos'))

@app.route('/admin/usuario/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(id):
    if not current_user.is_admin():
        flash('No tienes permiso para acceder a esta página.', 'danger')
        return redirect(url_for('index'))
    
    usuario = Usuario.query.get_or_404(id)
    
    if request.method == 'POST':
        usuario.nombre = request.form['nombre']
        usuario.email = request.form['email']
        usuario.direccion = request.form['direccion']
        usuario.telefono = request.form['telefono']
        usuario.tipo_usuario = request.form['tipo_usuario']
        
        if request.form.get('password'):
            usuario.password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        
        try:
            db.session.commit()
            flash('Usuario actualizado exitosamente.', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar el usuario.', 'danger')
    
    return render_template('admin/editar_usuario.html', usuario=usuario)

@app.route('/admin/usuario/eliminar/<int:id>')
@login_required
@admin_required
def eliminar_usuario(id):
    if not current_user.is_admin:
        flash('No tienes permiso para realizar esta acción', 'danger')
        return redirect(url_for('index'))
    
    usuario = Usuario.query.get_or_404(id)
    
    # No permitir eliminar el último administrador
    if usuario.tipo_usuario == 'admin':
        admin_count = Usuario.query.filter_by(tipo_usuario='admin').count()
        if admin_count <= 1:
            flash('No se puede eliminar el último administrador del sistema', 'danger')
            return redirect(url_for('admin_usuarios'))
    
    try:
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuario eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar el usuario', 'danger')
        print(f"Error: {str(e)}")
    
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuario/toggle_status/<int:id>')
@login_required
@admin_required
def toggle_user_status(id):
    if not current_user.is_admin:
        flash('No tienes permiso para realizar esta acción', 'danger')
        return redirect(url_for('index'))
    
    usuario = Usuario.query.get_or_404(id)
    
    # No permitir desactivar el último administrador
    if usuario.tipo_usuario == 'admin' and usuario.estado == 'activo':
        admin_count = Usuario.query.filter_by(tipo_usuario='admin', estado='activo').count()
        if admin_count <= 1:
            flash('No se puede desactivar el último administrador activo del sistema', 'danger')
            return redirect(url_for('admin_usuarios'))
    
    try:
        # Cambiar el estado del usuario
        usuario.estado = 'inactivo' if usuario.estado == 'activo' else 'activo'
        db.session.commit()
        
        estado_msg = 'activado' if usuario.estado == 'activo' else 'desactivado'
        flash(f'Usuario {estado_msg} exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al cambiar el estado del usuario', 'danger')
        print(f"Error: {str(e)}")
    
    return redirect(url_for('admin_usuarios'))

@app.route('/carrito/procesar', methods=['POST'])
@login_required
def procesar_pedido():
    try:
        # Validar que el carrito no esté vacío
        items = Carrito.query.filter_by(id_usuario=current_user.id_usuario).all()
        if not items:
            flash('El carrito está vacío', 'error')
            return redirect(url_for('carrito'))
        
        # Validar datos del cliente
        if not current_user.direccion or not current_user.telefono:
            flash('Debe completar su dirección y teléfono antes de realizar el pedido', 'error')
            return redirect(url_for('actualizar_perfil'))
        
        # Validar stock de productos
        for item in items:
            if item.cantidad > item.producto.stock:
                flash(f'No hay suficiente stock de {item.producto.nombre}', 'error')
                return redirect(url_for('carrito'))
        
        # Generar número de factura único
        numero_factura = f"F{datetime.now().strftime('%Y%m%d')}{Pedido.query.count() + 1:04d}"
        
        # Calcular totales e impuestos
        subtotal = sum(Decimal(str(item.producto.precio)) * item.cantidad for item in items)
        iva = subtotal * Decimal('0.13')  # 13% IVA
        total = subtotal + iva
        
        # Crear pedido
        pedido = Pedido(
            id_usuario=current_user.id_usuario,
            numero_factura=numero_factura,
            subtotal=subtotal,
            iva=iva,
            total=total,
            direccion_envio=current_user.direccion,
            telefono=current_user.telefono,
            estado='pendiente',
            metodo_pago=request.form.get('metodo_pago'),
            fecha_actualizacion=datetime.utcnow()
        )
        db.session.add(pedido)
        db.session.flush()
        
        # Crear detalles del pedido
        for item in items:
            detalle = DetallePedido(
                id_pedido=pedido.id_pedido,
                id_producto=item.id_producto,
                cantidad=item.cantidad,
                precio_unitario=item.producto.precio,
                subtotal=item.producto.precio * item.cantidad
            )
            db.session.add(detalle)
            
            # Actualizar stock
            producto = item.producto
            producto.stock -= item.cantidad
            if producto.stock < 0:
                db.session.rollback()
                flash('Stock insuficiente para algunos productos')
                return redirect(url_for('carrito'))
        
        # Limpiar carrito
        Carrito.query.filter_by(id_usuario=current_user.id_usuario).delete()
        
        db.session.commit()
        flash('Pedido procesado exitosamente', 'success')
        return redirect(url_for('ver_pedido', id=pedido.id_pedido))
        
    except Exception as e:
        db.session.rollback()
        flash('Error al procesar el pedido', 'error')
        print(f"Error: {str(e)}")
        return redirect(url_for('carrito'))

@app.route('/mis_pedidos')
@login_required
def mis_pedidos():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    pedidos = Pedido.query.filter_by(id_usuario=current_user.id_usuario).order_by(Pedido.fecha_pedido.desc()).all()
    return render_template('user/mis_pedidos.html', pedidos=pedidos)

@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/facturas/<int:id_factura>')
@login_required
def get_factura(id_factura):
    factura = Factura.query.get_or_404(id_factura)
    
    # Verificar permisos
    if not current_user.is_admin() and factura.pedido.id_usuario != current_user.id_usuario:
        return jsonify({'error': 'No autorizado'}), 403
    
    return jsonify({
        'id_factura': factura.id_factura,
        'numero_factura': factura.numero_factura,
        'fecha_emision': factura.fecha_emision.isoformat(),
        'estado': factura.estado,
        'subtotal': float(factura.subtotal),
        'iva': float(factura.iva),
        'total': float(factura.total),
        'pedido': {
            'id_pedido': factura.pedido.id_pedido,
            'usuario': {
                'nombre': factura.pedido.usuario.nombre,
                'nit': factura.pedido.usuario.nit
            },
            'direccion_envio': factura.pedido.direccion_envio,
            'telefono': factura.pedido.telefono,
            'detalles': [{
                'producto': {
                    'nombre': detalle.producto.nombre,
                    'imagen': detalle.producto.imagen
                },
                'cantidad': detalle.cantidad,
                'precio_unitario': float(detalle.precio_unitario),
                'subtotal': float(detalle.subtotal)
            } for detalle in factura.pedido.detalles]
        },
        'estados': [{
            'estado': estado.estado,
            'fecha_cambio': estado.fecha_cambio.isoformat(),
            'admin': {
                'nombre': estado.admin.nombre
            } if estado.admin else None,
            'observacion': estado.observacion
        } for estado in factura.estados]
    })

@app.route('/mis_facturas')
@login_required
def mis_facturas():
    # Obtener parámetros de filtrado
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    estado = request.args.get('estado')
    page = request.args.get('page', 1, type=int)
    
    # Construir la consulta base
    query = Factura.query.join(Pedido).filter(Pedido.id_usuario == current_user.id_usuario)
    
    # Aplicar filtros
    if fecha_desde:
        query = query.filter(Factura.fecha_emision >= datetime.strptime(fecha_desde, '%Y-%m-%d'))
    if fecha_hasta:
        query = query.filter(Factura.fecha_emision <= datetime.strptime(fecha_hasta, '%Y-%m-%d'))
    if estado:
        query = query.filter(Factura.estado == estado)
    
    # Ordenar por fecha de emisión descendente
    query = query.order_by(Factura.fecha_emision.desc())
    
    # Paginar resultados
    pagination = query.paginate(page=page, per_page=10)
    
    return render_template('user/facturas.html', 
                         facturas=pagination.items,
                         pagination=pagination)

@app.route('/admin/facturas/<int:id_factura>/anular', methods=['POST'])
@login_required
@admin_required
def anular_factura(id_factura):
    if not current_user.is_admin():
        return jsonify({'error': 'No autorizado'}), 403
    
    factura = Factura.query.get_or_404(id_factura)
    
    if factura.estado != 'emitida':
        return jsonify({'error': 'Solo se pueden anular facturas emitidas'}), 400
    
    motivo = request.form.get('motivo')
    if not motivo:
        return jsonify({'error': 'El motivo de anulación es requerido'}), 400
    
    try:
        # Actualizar estado de la factura
        factura.estado = 'anulada'
        
        # Registrar el cambio de estado
        nuevo_estado = EstadoFactura(
            id_factura=factura.id_factura,
            estado='anulada',
            id_admin=current_user.id_usuario,
            observacion=motivo
        )
        db.session.add(nuevo_estado)
        
        db.session.commit()
        flash('Factura anulada exitosamente', 'success')
        return redirect(url_for('admin_facturas'))
    except Exception as e:
        db.session.rollback()
        flash('Error al anular la factura', 'danger')
        return redirect(url_for('admin_facturas'))

@app.route('/factura/emitir/<int:id_pedido>', methods=['POST'])
@login_required
def emitir_factura(id_pedido):
    pedido = Pedido.query.get_or_404(id_pedido)
    
    # Verificar que el usuario sea el propietario del pedido o un administrador
    if not current_user.is_admin() and pedido.id_usuario != current_user.id_usuario:
        flash('No tienes permiso para emitir esta factura', 'danger')
        return redirect(url_for('index'))
    
    # Verificar si ya existe una factura para este pedido
    if hasattr(pedido, 'factura'):
        flash('Este pedido ya tiene una factura emitida', 'warning')
        return redirect(url_for('ver_pedido', id=id_pedido))
    
    try:
        # Recalcular totales
        subtotal = Decimal('0.00')
        for detalle in pedido.detalles:
            subtotal += detalle.precio_unitario * detalle.cantidad
        
        iva = subtotal * Decimal('0.13')  # 13% IVA
        total = subtotal + iva
        
        # Actualizar totales en el pedido
        pedido.subtotal = subtotal
        pedido.iva = iva
        pedido.total = total
        
        # Generar número de factura
        ultima_factura = Factura.query.order_by(Factura.id_factura.desc()).first()
        nuevo_numero = 1 if not ultima_factura else int(ultima_factura.numero_factura.split('-')[1]) + 1
        numero_factura = f'FACT-{nuevo_numero:06d}'
        
        # Generar número de voucher único
        fecha_actual = datetime.utcnow()
        voucher_number = f'VOU-{fecha_actual.strftime("%Y%m%d")}-{nuevo_numero:06d}'
        
        # Crear la factura con los totales calculados
        factura = Factura(
            id_pedido=pedido.id_pedido,
            numero_factura=numero_factura,
            voucher_number=voucher_number,
            subtotal=subtotal,
            iva=iva,
            total=total
        )
        db.session.add(factura)
        
        # Registrar el estado inicial
        estado_inicial = EstadoFactura(
            id_factura=factura.id_factura,
            estado='emitida',
            id_admin=current_user.id_usuario,
            observacion='Factura emitida inicialmente'
        )
        db.session.add(estado_inicial)
        
        db.session.commit()
        
        # Generar PDF de la factura
        generar_pdf_factura(factura)
        
        flash('Factura emitida exitosamente', 'success')
        return redirect(url_for('ver_pedido', id=id_pedido))
        
    except Exception as e:
        db.session.rollback()
        flash('Error al emitir la factura', 'danger')
        print(f"Error al emitir factura: {str(e)}")
        return redirect(url_for('ver_pedido', id=id_pedido))

@app.route('/factura/descargar/<int:id_factura>')
@login_required
def descargar_factura(id_factura):
    factura = Factura.query.get_or_404(id_factura)
    
    # Verificar que el usuario sea el propietario del pedido o un administrador
    if not current_user.is_admin() and factura.pedido.id_usuario != current_user.id_usuario:
        flash('No tienes permiso para descargar esta factura', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Generar el PDF si no existe
        pdf_path = generar_pdf_factura(factura)
        if not pdf_path:
            flash('Error al generar el PDF de la factura', 'danger')
            if current_user.is_admin():
                return redirect(url_for('ver_pedido_admin', id=factura.id_pedido))
            else:
                return redirect(url_for('ver_pedido', id=factura.id_pedido))
        
        # Actualizar la ruta del PDF en la base de datos
        factura.pdf_path = pdf_path
        db.session.commit()
        
        # Enviar el archivo
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f'factura_{factura.numero_factura}.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Error al descargar factura: {str(e)}")
        flash(f'Error al descargar la factura: {str(e)}', 'danger')
        if current_user.is_admin():
            return redirect(url_for('ver_pedido_admin', id=factura.id_pedido))
        else:
            return redirect(url_for('ver_pedido', id=factura.id_pedido))

def generar_pdf_factura(factura):
    try:
        # Crear el directorio si no existe
        pdf_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'facturas')
        os.makedirs(pdf_dir, exist_ok=True)
        
        # Nombre del archivo PDF
        pdf_filename = f'factura_{factura.numero_factura}.pdf'
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        
        # Crear el documento PDF con márgenes personalizados
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Lista para almacenar los elementos del PDF
        elements = []
        
        # Estilos personalizados
        styles = getSampleStyleSheet()
        
        # Estilo para el título principal
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),  # Azul oscuro
            spaceAfter=30,
            alignment=1  # Centrado
        )
        
        # Estilo para subtítulos
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#303f9f'),  # Azul medio
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Estilo para texto normal
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Estilo para texto en negrita
        bold_style = ParagraphStyle(
            'CustomBold',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            spaceAfter=6
        )
        
        # Estilo para totales
        total_style = ParagraphStyle(
            'CustomTotal',
            parent=styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1a237e'),  # Azul oscuro
            spaceAfter=6
        )
        
        # Logo y encabezado
        elements.append(Paragraph("TECHSTORE", title_style))
        elements.append(Spacer(1, 20))
        
        # Línea decorativa
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a237e'), spaceBefore=10, spaceAfter=10))
        
        # Información de la empresa y factura en dos columnas
        empresa_data = [
            ["DATOS DE LA EMPRESA", "DATOS DE LA FACTURA"],
            ["TechStore", f"N° Factura: {factura.numero_factura}"],
            ["NIT: 1234567890", f"N° Voucher: {factura.voucher_number}"],
            ["Dirección: Calle Apruebenos Ingeniero #100", f"Fecha: {factura.fecha_emision.strftime('%d/%m/%Y %H:%M')}"],
            ["Teléfono: +591 75781303", f"Estado: {factura.estado.title()}"],
            ["Email: techstore@gmail.com", ""]
        ]
        
        # Estilo para la tabla de información
        info_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8eaf6')),  # Fondo azul claro
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a237e')),  # Texto azul oscuro
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#c5cae9')),  # Borde azul claro
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ])
        
        info_table = Table(empresa_data, colWidths=[250, 250])
        info_table.setStyle(info_style)
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        # Información del cliente
        elements.append(Paragraph("DATOS DEL CLIENTE", subtitle_style))
        cliente = factura.pedido.usuario
        cliente_data = [
            ["Nombre:", cliente.nombre],
            ["NIT:", cliente.nit or "No especificado"],
            ["Email:", cliente.email],
            ["Teléfono:", cliente.telefono],
            ["Dirección:", cliente.direccion]
        ]
        
        cliente_style = TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#c5cae9')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a237e')),
        ])
        
        cliente_table = Table(cliente_data, colWidths=[100, 400])
        cliente_table.setStyle(cliente_style)
        elements.append(cliente_table)
        elements.append(Spacer(1, 20))
        
        # Detalles del pedido
        elements.append(Paragraph("DETALLES DEL PEDIDO", subtitle_style))
        
        # Calcular subtotales y totales
        subtotal = Decimal('0.00')
        data = [['Producto', 'Cantidad', 'Precio Unit.', 'Subtotal']]
        
        for detalle in factura.pedido.detalles:
            subtotal_producto = detalle.precio_unitario * detalle.cantidad
            subtotal += subtotal_producto
            data.append([
                detalle.producto.nombre,
                str(detalle.cantidad),
                f"Bs. {detalle.precio_unitario:.2f}",
                f"Bs. {subtotal_producto:.2f}"
            ])
        
        # Calcular IVA y total
        iva = subtotal * Decimal('0.13')
        total = subtotal + iva
        
        # Estilo para la tabla de productos
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),  # Fondo azul oscuro
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),  # Texto blanco
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#c5cae9')),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),  # Filas alternadas
        ])
        
        table = Table(data, colWidths=[250, 80, 100, 100])
        table.setStyle(table_style)
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        # Totales
        totales_data = [
            ["Subtotal:", f"Bs. {subtotal:.2f}"],
            ["IVA (13%):", f"Bs. {iva:.2f}"],
            ["Total:", f"Bs. {total:.2f}"]
        ]
        
        totales_style = TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#c5cae9')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a237e')),
        ])
        
        totales_table = Table(totales_data, colWidths=[100, 100])
        totales_table.setStyle(totales_style)
        elements.append(totales_table)
        elements.append(Spacer(1, 30))
        
        # Pie de página
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a237e'), spaceBefore=10, spaceAfter=10))
        elements.append(Paragraph("CONDICIONES Y TÉRMINOS", subtitle_style))
        
        condiciones = [
            "• Esta factura es un documento legal y oficial",
            "• Los productos tienen garantía de 1 año",
            "• Para soporte técnico contacte a techstore@gmail.com",
            "• Gracias por su preferencia"
        ]
        
        for condicion in condiciones:
            elements.append(Paragraph(condicion, normal_style))
        
        elements.append(Spacer(1, 30))
        
        # Firma
        firma_data = [
            ["_______________________", "_______________________"],
            ["Firma Autorizada", "Sello de la Empresa"]
        ]
        
        firma_style = TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ])
        
        firma_table = Table(firma_data, colWidths=[200, 200])
        firma_table.setStyle(firma_style)
        elements.append(firma_table)
        
        # Construir el PDF
        doc.build(elements)
        
        # Actualizar la ruta del PDF en la factura
        factura.pdf_path = pdf_path
        db.session.commit()
        
        return pdf_path
        
    except Exception as e:
        print(f"Error al generar PDF: {str(e)}")
        return None

@app.route('/admin/usuario/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_usuario():
    if not current_user.is_admin:
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre')
            email = request.form.get('email')
            password = request.form.get('password')
            tipo_usuario = request.form.get('tipo_usuario')
            nit = request.form.get('nit')
            direccion = request.form.get('direccion')
            telefono = request.form.get('telefono')
            
            # Validaciones
            if not all([nombre, email, password, tipo_usuario]):
                flash('Todos los campos obligatorios deben ser completados', 'danger')
                return redirect(url_for('crear_usuario'))
            
            if not validar_email(email):
                flash('El email no es válido', 'danger')
                return redirect(url_for('crear_usuario'))
            
            if nit and not validar_nit(nit):
                flash('El NIT debe contener 11 dígitos', 'danger')
                return redirect(url_for('crear_usuario'))
            
            if telefono and not validar_telefono(telefono):
                flash('El teléfono debe contener al menos 7 dígitos', 'danger')
                return redirect(url_for('crear_usuario'))
            
            # Verificar si el email ya existe
            if Usuario.query.filter_by(email=email).first():
                flash('El email ya está registrado', 'danger')
                return redirect(url_for('crear_usuario'))
            
            # Verificar si el NIT ya existe
            if nit and Usuario.query.filter_by(nit=nit).first():
                flash('El NIT ya está registrado', 'danger')
                return redirect(url_for('crear_usuario'))
            
            # Crear nuevo usuario
            nuevo_usuario = Usuario(
                nombre=nombre,
                email=email,
                password=generate_password_hash(password),
                tipo_usuario=tipo_usuario,
                nit=nit,
                direccion=direccion,
                telefono=telefono,
                estado='activo'
            )
            
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            flash('Usuario creado exitosamente', 'success')
            return redirect(url_for('admin_usuarios'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error al crear el usuario', 'danger')
            print(f"Error al crear usuario: {str(e)}")
            return redirect(url_for('crear_usuario'))
    
    return render_template('admin/crear_usuario.html')

@app.route('/pedido/cancelar/<int:id>', methods=['POST'])
@login_required
def cancelar_pedido(id):
    try:
        pedido = Pedido.query.get_or_404(id)
        
        # Verificar que el pedido pertenece al usuario actual
        if pedido.id_usuario != current_user.id_usuario:
            flash('No tienes permiso para cancelar este pedido', 'danger')
            return redirect(url_for('user_dashboard'))
        
        # Verificar que el pedido está pendiente
        if pedido.estado != 'pendiente':
            flash('Solo se pueden cancelar pedidos pendientes', 'warning')
            return redirect(url_for('user_dashboard'))
        
        # Actualizar estado del pedido
        pedido.estado = 'cancelado'
        pedido.fecha_actualizacion = datetime.utcnow()
        
        # Devolver productos al stock
        for detalle in pedido.detalles:
            producto = detalle.producto
            producto.stock += detalle.cantidad
        
        db.session.commit()
        flash('Pedido cancelado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error al cancelar el pedido', 'danger')
        print(f"Error: {str(e)}")
    
    return redirect(url_for('user_dashboard'))

@app.route('/paypal/create-payment', methods=['GET', 'POST'])
@login_required
def create_paypal_payment():
    try:
        print("\n=== Iniciando proceso de pago PayPal ===")
        print(f"Usuario actual: {current_user.id_usuario}")
        
        # Obtener el total del carrito
        items = Carrito.query.filter_by(id_usuario=current_user.id_usuario).all()
        print(f"Items en carrito: {len(items)}")
        
        if not items:
            print("Error: Carrito vacío")
            flash('El carrito está vacío', 'error')
            return redirect(url_for('carrito'))
            
        total = sum(Decimal(str(item.producto.precio)) * item.cantidad for item in items)
        print(f"Total del carrito: {total}")
        
        # Verificar que el total sea válido
        if total <= 0:
            print("Error: Total inválido (menor o igual a 0)")
            flash('El monto total debe ser mayor a 0', 'error')
            return redirect(url_for('carrito'))
        
        if PAYPAL_SIMULATION:
            print("Modo simulación activado")
            # En modo simulación, crear un ID de pago simulado
            payment_id = f"PAY-SIM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            session['paypal_payment_id'] = payment_id
            session['paypal_simulation'] = True
            subtotal = sum(Decimal(str(item.producto.precio)) * item.cantidad for item in items)
            iva = subtotal * Decimal('0.13')
            total = (subtotal + iva).quantize(Decimal('0.01'))
            session['paypal_amount'] = str(total)
            session['paypal_user_id'] = current_user.id_usuario
            
            print(f"ID de pago simulado creado: {payment_id}")
            print("Redirigiendo a página de simulación")
            return redirect(url_for('paypal_simulation'))
        
        print("Modo PayPal real activado")
        # Crear el pago en PayPal (modo real)
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": url_for('paypal_execute', _external=True),
                "cancel_url": url_for('paypal_cancel', _external=True)
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": "Compra en TechStore",
                        "sku": "TS001",
                        "price": str(total),
                        "currency": "BOB",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(total),
                    "currency": "BOB"
                },
                "description": "Compra en TechStore"
            }]
        })

        print(f"Configuración PayPal:")
        print(f"- Mode: {PAYPAL_MODE}")
        print(f"- Client ID configurado: {'Sí' if PAYPAL_CLIENT_ID else 'No'}")
        print(f"- Monto: {total}")

        if payment.create():
            print(f"Pago PayPal creado exitosamente. ID: {payment.id}")
            session['paypal_payment_id'] = payment.id
            session['paypal_simulation'] = False
            session['paypal_amount'] = str(total)
            session['paypal_user_id'] = current_user.id_usuario
            
            for link in payment.links:
                if link.rel == "approval_url":
                    print(f"URL de aprobación: {link.href}")
                    return redirect(link.href)
        else:
            error_message = f"Error al crear el pago en PayPal: {payment.error}"
            print(error_message)
            flash('Error al crear el pago en PayPal. Por favor, intente nuevamente.', 'error')
            return redirect(url_for('checkout'))
            
    except Exception as e:
        error_message = f"Error en create_paypal_payment: {str(e)}"
        print(error_message)
        print(f"Tipo de error: {type(e)}")
        import traceback
        print(f"Traceback completo:\n{traceback.format_exc()}")
        flash('Error al procesar el pago. Por favor, intente nuevamente.', 'error')
        return redirect(url_for('checkout'))

@app.route('/paypal/simulation')
@login_required
def paypal_simulation():
    try:
        print("\n=== Página de simulación PayPal ===")
        print(f"Usuario actual: {current_user.id_usuario}")
        print(f"Modo simulación activo: {session.get('paypal_simulation')}")
        print(f"ID de pago: {session.get('paypal_payment_id')}")
        print(f"Monto: {session.get('paypal_amount')}")
        
        if not session.get('paypal_simulation'):
            print("Error: Modo simulación no activo")
            return redirect(url_for('checkout'))
        
        # Verificar que el usuario actual sea el mismo que inició el pago
        if session.get('paypal_user_id') != current_user.id_usuario:
            print(f"Error de autenticación: Usuario actual {current_user.id_usuario} != Usuario del pago {session.get('paypal_user_id')}")
            flash('Error de autenticación en el pago', 'error')
            return redirect(url_for('checkout'))
        
        return render_template('paypal_simulation.html')
        
    except Exception as e:
        print(f"Error en paypal_simulation: {str(e)}")
        print(f"Tipo de error: {type(e)}")
        import traceback
        print(f"Traceback completo:\n{traceback.format_exc()}")
        flash('Error al acceder a la simulación. Por favor, intente nuevamente.', 'error')
        return redirect(url_for('checkout'))

@app.route('/paypal/simulation/execute', methods=['POST'])
@login_required
def paypal_simulation_execute():
    try:
        print("\n=== Ejecutando simulación PayPal ===")
        print(f"Usuario actual: {current_user.id_usuario}")
        print(f"Modo simulación activo: {session.get('paypal_simulation')}")
        print(f"ID de pago: {session.get('paypal_payment_id')}")
        print(f"Monto: {session.get('paypal_amount')}")
        
        # Verificar que el usuario actual sea el mismo que inició el pago
        if session.get('paypal_user_id') != current_user.id_usuario:
            print(f"Error de autenticación en simulación: Usuario actual {current_user.id_usuario} != Usuario del pago {session.get('paypal_user_id')}")
            flash('Error de autenticación en el pago', 'error')
            return redirect(url_for('checkout'))
        
        # Verificar que el carrito no esté vacío
        items = Carrito.query.filter_by(id_usuario=current_user.id_usuario).all()
        if not items:
            print("Error: Carrito vacío en simulación")
            flash('El carrito está vacío', 'error')
            return redirect(url_for('carrito'))
        
        # Verificar datos del cliente
        if not current_user.direccion or not current_user.telefono:
            print(f"Error: Datos de cliente incompletos en simulación - Dirección: {bool(current_user.direccion)}, Teléfono: {bool(current_user.telefono)}")
            flash('Debe completar su dirección y teléfono antes de realizar el pedido', 'error')
            return redirect(url_for('actualizar_perfil'))
        
        # Verificar stock
        for item in items:
            if item.cantidad > item.producto.stock:
                print(f"Error: Stock insuficiente en simulación para {item.producto.nombre} - Cantidad: {item.cantidad}, Stock: {item.producto.stock}")
                flash(f'No hay suficiente stock de {item.producto.nombre}', 'error')
                return redirect(url_for('carrito'))
        
        payment_id = session.get('paypal_payment_id')
        if not payment_id:
            print("Error: No se encontró ID de pago en la simulación")
            flash('No se encontró información del pago', 'error')
            return redirect(url_for('checkout'))
        
        print(f"Iniciando simulación de pago exitoso - ID: {payment_id}")
        
        # Calcular total para verificación
        subtotal = sum(Decimal(str(item.producto.precio)) * item.cantidad for item in items)
        iva = subtotal * Decimal('0.13')
        total = (subtotal + iva).quantize(Decimal('0.01'))
        paypal_amount = Decimal(str(session.get('paypal_amount', 0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        print(f"[DEBUG] Total calculado: {total}")
        print(f"[DEBUG] Monto PayPal de sesión: {paypal_amount}")
        print(f"[DEBUG] Diferencia absoluta: {abs(total - paypal_amount)}")

        if abs(total - paypal_amount) > Decimal('0.01'):  # Comparación directa en bolivianos
            error_message = f"Error en monto: Total ({total}) != PayPal ({paypal_amount})"
            print(error_message)
            flash('Error en el monto del pago. Por favor, intente nuevamente.', 'error')
            return redirect(url_for('carrito'))
        
        # Iniciar transacción
        try:
            # Crear pedido
            pedido = Pedido(
                id_usuario=current_user.id_usuario,
                # numero_factura se asignará en el trigger
                subtotal=subtotal,
                iva=iva,
                total=total,
                direccion_envio=current_user.direccion,
                telefono=current_user.telefono,
                estado='pendiente',
                metodo_pago='paypal',
                paypal_payment_id=payment_id,
                fecha_actualizacion=datetime.utcnow()
            )
            db.session.add(pedido)
            db.session.flush()  # Obtener el ID del pedido
            
            print(f"Pedido creado - ID: {pedido.id_pedido}") # Eliminar numero_factura de este print
            
            # Crear detalles del pedido
            for item in items:
                detalle = DetallePedido(
                    id_pedido=pedido.id_pedido,
                    id_producto=item.id_producto,
                    cantidad=item.cantidad,
                    precio_unitario=item.producto.precio,
                    subtotal=item.producto.precio * item.cantidad
                )
                db.session.add(detalle)
                
                # Actualizar stock
                producto = item.producto
                producto.stock -= item.cantidad
                if producto.stock < 0:
                    raise ValueError(f"Stock insuficiente para {producto.nombre}")
                db.session.add(producto)
                
                print(f"Detalle agregado - Producto: {producto.nombre}, Cantidad: {item.cantidad}")
            
            # Limpiar carrito y sesión de PayPal
            Carrito.query.filter_by(id_usuario=current_user.id_usuario).delete()
            session.pop('paypal_payment_id', None)
            session.pop('paypal_simulation', None)
            session.pop('paypal_user_id', None)
            session.pop('paypal_amount', None)
            
            # Confirmar transacción
            db.session.commit()
            
            print(f"Pedido procesado exitosamente - ID: {pedido.id_pedido}") # Eliminar numero_factura de este print
            flash('Pedido procesado exitosamente', 'success')
            return redirect(url_for('ver_pedido', id=pedido.id_pedido))
            
        except ValueError as ve:
            db.session.rollback()
            print(f"Error de validación: {str(ve)}")
            flash(str(ve), 'error')
            return redirect(url_for('carrito'))
        except Exception as e:
            db.session.rollback()
            print(f"Error en la transacción: {str(e)}")
            print(f"Tipo de error: {type(e)}")
            import traceback
            print(f"Traceback completo:\n{traceback.format_exc()}")
            flash('Error al procesar el pedido. Por favor, intente nuevamente.', 'error')
            return redirect(url_for('carrito'))
            
    except Exception as e:
        print(f"Error general en paypal_simulation_execute: {str(e)}")
        print(f"Tipo de error: {type(e)}")
        import traceback
        print(f"Traceback completo:\n{traceback.format_exc()}")
        flash('Error al procesar la simulación. Por favor, intente nuevamente.', 'error')
        return redirect(url_for('checkout'))

@app.route('/paypal/simulation/cancel')
@login_required
def paypal_simulation_cancel():
    # Verificar que el usuario actual sea el mismo que inició el pago
    if session.get('paypal_user_id') != current_user.id_usuario:
        flash('Error de autenticación en el pago', 'error')
        return redirect(url_for('checkout'))
    
    session.pop('paypal_payment_id', None)
    session.pop('paypal_simulation', None)
    session.pop('paypal_user_id', None)
    flash('Pago cancelado', 'info')
    return redirect(url_for('checkout'))

@app.route('/paypal/execute')
@login_required
def paypal_execute():
    try:
        payment_id = session.get('paypal_payment_id')
        if not payment_id:
            flash('No se encontró información del pago', 'error')
            return redirect(url_for('checkout'))

        # Verificar que el usuario actual sea el mismo que inició el pago
        if session.get('paypal_user_id') != current_user.id_usuario:
            flash('Error de autenticación en el pago', 'error')
            return redirect(url_for('checkout'))

        if session.get('paypal_simulation'):
            # Si es una simulación, procesar directamente
            return redirect(url_for('procesar_pedido_paypal', payment_id=payment_id))

        # Proceso real de PayPal
        print(f"Ejecutando pago PayPal. ID: {payment_id}")
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if payment.execute({"payer_id": request.args.get('PayerID')}):
            print(f"Pago PayPal ejecutado exitosamente. ID: {payment_id}")
            return redirect(url_for('procesar_pedido_paypal', payment_id=payment_id))
        else:
            error_message = f"Error al ejecutar el pago en PayPal: {payment.error}"
            print(error_message)
            flash('Error al ejecutar el pago en PayPal. Por favor, intente nuevamente.', 'error')
            return redirect(url_for('checkout'))
            
    except Exception as e:
        error_message = f"Error en paypal_execute: {str(e)}"
        print(error_message)
        flash('Error al procesar el pago. Por favor, intente nuevamente.', 'error')
        return redirect(url_for('checkout'))

@app.route('/paypal/cancel')
@login_required
def paypal_cancel():
    # Verificar que el usuario actual sea el mismo que inició el pago
    if session.get('paypal_user_id') != current_user.id_usuario:
        flash('Error de autenticación en el pago', 'error')
        return redirect(url_for('checkout'))
    
    session.pop('paypal_payment_id', None)
    session.pop('paypal_simulation', None)
    session.pop('paypal_user_id', None)
    flash('Pago cancelado', 'info')
    return redirect(url_for('checkout'))

@app.route('/paypal/process-order/<payment_id>')
@login_required
def procesar_pedido_paypal(payment_id):
    try:
        print("\n=== Procesando pedido PayPal ===")
        print(f"Usuario actual: {current_user.id_usuario}")
        print(f"ID de pago: {payment_id}")
        
        # Verificar que el usuario actual sea el mismo que inició el pago
        if session.get('paypal_user_id') != current_user.id_usuario:
            print(f"Error de autenticación: Usuario actual {current_user.id_usuario} != Usuario del pago {session.get('paypal_user_id')}")
            flash('Error de autenticación en el pago', 'error')
            return redirect(url_for('checkout'))
        
        # Validar que el carrito no esté vacío
        items = Carrito.query.filter_by(id_usuario=current_user.id_usuario).all()
        if not items:
            print("Error: Carrito vacío")
            flash('El carrito está vacío', 'error')
            return redirect(url_for('carrito'))
        
        # Validar datos del cliente
        if not current_user.direccion or not current_user.telefono:
            print(f"Error: Datos de cliente incompletos - Dirección: {bool(current_user.direccion)}, Teléfono: {bool(current_user.telefono)}")
            flash('Debe completar su dirección y teléfono antes de realizar el pedido', 'error')
            return redirect(url_for('actualizar_perfil'))
        
        # Validar stock de productos
        for item in items:
            if item.cantidad > item.producto.stock:
                print(f"Error: Stock insuficiente para {item.producto.nombre} - Cantidad: {item.cantidad}, Stock: {item.producto.stock}")
                flash(f'No hay suficiente stock de {item.producto.nombre}', 'error')
                return redirect(url_for('carrito'))
        
        # Generar número de factura único
        # numero_factura se genera en el trigger before_pedido_insert
        # numero_factura = f"F{datetime.now().strftime('%Y%m%d')}{Pedido.query.count() + 1:04d}"
        
        # Calcular totales e impuestos
        subtotal = sum(Decimal(str(item.producto.precio)) * item.cantidad for item in items)
        iva = subtotal * Decimal('0.13')  # 13% IVA
        total = (subtotal + iva).quantize(Decimal('0.01'))
        
        # Verificar que el total coincida con el monto de PayPal
        paypal_amount = Decimal(str(session.get('paypal_amount', 0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if abs(total - paypal_amount) > Decimal('0.01'):  # Comparación directa en bolivianos
            error_message = f"Error en monto: Total ({total}) != PayPal ({paypal_amount})"
            print(error_message)
            flash('Error en el monto del pago. Por favor, intente nuevamente.', 'error')
            return redirect(url_for('carrito'))
        
        # Iniciar transacción
        try:
            # Crear pedido
            pedido = Pedido(
                id_usuario=current_user.id_usuario,
                # numero_factura se asignará en el trigger
                subtotal=subtotal,
                iva=iva,
                total=total,
                direccion_envio=current_user.direccion,
                telefono=current_user.telefono,
                estado='pendiente',
                metodo_pago='paypal',
                paypal_payment_id=payment_id,
                fecha_actualizacion=datetime.utcnow()
            )
            db.session.add(pedido)
            db.session.flush()  # Obtener el ID del pedido
            
            print(f"Pedido creado - ID: {pedido.id_pedido}")
            
            # Crear detalles del pedido
            for item in items:
                detalle = DetallePedido(
                    id_pedido=pedido.id_pedido,
                    id_producto=item.id_producto,
                    cantidad=item.cantidad,
                    precio_unitario=item.producto.precio,
                    subtotal=item.producto.precio * item.cantidad
                )
                db.session.add(detalle)
                
                # Actualizar stock
                producto = item.producto
                producto.stock -= item.cantidad
                if producto.stock < 0:
                    raise ValueError(f"Stock insuficiente para {producto.nombre}")
                db.session.add(producto)
                
                print(f"Detalle agregado - Producto: {producto.nombre}, Cantidad: {item.cantidad}")
            
            # Limpiar carrito y sesión de PayPal
            Carrito.query.filter_by(id_usuario=current_user.id_usuario).delete()
            session.pop('paypal_payment_id', None)
            session.pop('paypal_simulation', None)
            session.pop('paypal_user_id', None)
            session.pop('paypal_amount', None)
            
            # Confirmar transacción
            db.session.commit()
            
            print(f"Pedido procesado exitosamente - ID: {pedido.id_pedido}")
            flash('Pedido procesado exitosamente', 'success')
            return redirect(url_for('ver_pedido', id=pedido.id_pedido))
            
        except ValueError as ve:
            db.session.rollback()
            print(f"Error de validación: {str(ve)}")
            flash(str(ve), 'error')
            return redirect(url_for('carrito'))
        except Exception as e:
            db.session.rollback()
            print(f"Error en la transacción: {str(e)}")
            print(f"Tipo de error: {type(e)}")
            import traceback
            print(f"Traceback completo:\n{traceback.format_exc()}")
            flash('Error al procesar el pedido. Por favor, intente nuevamente.', 'error')
            return redirect(url_for('carrito'))
            
    except Exception as e:
        print(f"Error general en procesar_pedido_paypal: {str(e)}")
        print(f"Tipo de error: {type(e)}")
        import traceback
        print(f"Traceback completo:\n{traceback.format_exc()}")
        flash('Error al procesar el pedido. Por favor, intente nuevamente.', 'error')
        return redirect(url_for('carrito'))

# API para el bot de ayuda
@app.route('/api/bot/buscar_productos', methods=['POST'])
def api_bot_buscar_productos():
    try:
        data = request.get_json()
        query = data.get('query', '').lower()
        categoria = data.get('categoria', '').lower()
        precio_max = data.get('precio_max', None)
        precio_min = data.get('precio_min', None)
        
        # Construir consulta base
        productos_query = Producto.query.filter_by(estado='activo')
        
        # Filtrar por búsqueda de texto
        if query:
            productos_query = productos_query.filter(
                (Producto.nombre.ilike(f'%{query}%')) |
                (Producto.descripcion.ilike(f'%{query}%'))
            )
        
        # Filtrar por categoría
        if categoria:
            categoria_obj = Categoria.query.filter(
                Categoria.nombre.ilike(f'%{categoria}%')
            ).first()
            if categoria_obj:
                productos_query = productos_query.filter_by(id_categoria=categoria_obj.id_categoria)
        
        # Filtrar por precio
        if precio_max:
            productos_query = productos_query.filter(Producto.precio <= float(precio_max))
        if precio_min:
            productos_query = productos_query.filter(Producto.precio >= float(precio_min))
        
        productos = productos_query.order_by(Producto.precio).limit(10).all()
        
        # Formatear respuesta
        productos_data = []
        for producto in productos:
            productos_data.append({
                'id': producto.id_producto,
                'nombre': producto.nombre,
                'descripcion': producto.descripcion or 'Sin descripción',
                'precio': float(producto.precio),
                'stock': producto.stock,
                'categoria': producto.categoria.nombre if producto.categoria else 'Sin categoría',
                'url': url_for('producto', id=producto.id_producto)
            })
        
        return jsonify({
            'success': True,
            'productos': productos_data,
            'total': len(productos_data)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bot/recomendar', methods=['POST'])
def api_bot_recomendar():
    try:
        data = request.get_json()
        necesidad = data.get('necesidad', '').lower()
        presupuesto = data.get('presupuesto', None)
        uso = data.get('uso', '').lower()
        
        # Palabras clave para categorías
        categorias_keywords = {
            'smartphone': ['smartphone', 'celular', 'telefono', 'teléfono', 'móvil', 'movil', 'iphone', 'samsung', 'huawei'],
            'laptop': ['laptop', 'portatil', 'portátil', 'notebook', 'computadora', 'pc portatil', 'macbook'],
            'tablet': ['tablet', 'ipad', 'tableta'],
            'accesorio': ['accesorio', 'auricular', 'audifono', 'cargador', 'cable', 'case', 'funda', 'protector']
        }
        
        # Determinar categoría basada en necesidad
        categoria_id = None
        categoria_nombre = None
        for cat_name, keywords in categorias_keywords.items():
            if any(keyword in necesidad for keyword in keywords):
                categoria_obj = Categoria.query.filter(
                    Categoria.nombre.ilike(f'%{cat_name}%')
                ).first()
                if categoria_obj:
                    categoria_id = categoria_obj.id_categoria
                    categoria_nombre = categoria_obj.nombre
                    break
        
        # Construir consulta
        productos_query = Producto.query.filter_by(estado='activo')
        
        if categoria_id:
            productos_query = productos_query.filter_by(id_categoria=categoria_id)
        
        # Filtrar por presupuesto
        if presupuesto:
            try:
                presupuesto_float = float(presupuesto)
                productos_query = productos_query.filter(Producto.precio <= presupuesto_float)
            except:
                pass
        
        # Ordenar por precio (más económico primero) o por stock
        if 'economico' in necesidad or 'barato' in necesidad or 'precio' in necesidad:
            productos_query = productos_query.order_by(Producto.precio)
        elif 'mejor' in necesidad or 'calidad' in necesidad or 'premium' in necesidad:
            productos_query = productos_query.order_by(Producto.precio.desc())
        else:
            productos_query = productos_query.order_by(Producto.stock.desc(), Producto.precio)
        
        productos = productos_query.limit(5).all()
        
        # Formatear respuesta
        productos_data = []
        for producto in productos:
            productos_data.append({
                'id': producto.id_producto,
                'nombre': producto.nombre,
                'descripcion': producto.descripcion or 'Sin descripción',
                'precio': float(producto.precio),
                'stock': producto.stock,
                'categoria': producto.categoria.nombre if producto.categoria else 'Sin categoría',
                'url': url_for('producto', id=producto.id_producto)
            })
        
        return jsonify({
            'success': True,
            'productos': productos_data,
            'categoria': categoria_nombre,
            'total': len(productos_data)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bot/categorias', methods=['GET'])
def api_bot_categorias():
    try:
        categorias = Categoria.query.all()
        categorias_data = [{'id': cat.id_categoria, 'nombre': cat.nombre} for cat in categorias]
        return jsonify({
            'success': True,
            'categorias': categorias_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bot/chat', methods=['POST'])
def api_bot_chat():
    """
    API unificada para el bot de ayuda
    Procesa mensajes del usuario y devuelve respuestas inteligentes
    """
    try:
        data = request.get_json()
        mensaje = data.get('mensaje', '').strip()
        
        if not mensaje:
            return jsonify({
                'success': False,
                'error': 'Mensaje vacío'
            }), 400
        
        mensaje_lower = mensaje.lower()
        
        # Detectar intención del usuario
        intencion = detectar_intencion(mensaje_lower)
        
        if intencion['tipo'] == 'buscar':
            # Buscar productos
            productos = buscar_productos_bot(
                query=intencion.get('query', ''),
                categoria=intencion.get('categoria'),
                precio_max=intencion.get('precio_max'),
                precio_min=intencion.get('precio_min')
            )
            
            return jsonify({
                'success': True,
                'tipo': 'buscar',
                'productos': productos,
                'total': len(productos),
                'mensaje': f"Encontré {len(productos)} producto(s) para ti"
            })
        
        elif intencion['tipo'] == 'recomendar':
            # Recomendar productos
            productos = recomendar_productos_bot(
                necesidad=mensaje,
                presupuesto=intencion.get('presupuesto'),
                uso=intencion.get('uso')
            )
            
            return jsonify({
                'success': True,
                'tipo': 'recomendar',
                'productos': productos['productos'],
                'categoria': productos.get('categoria'),
                'total': len(productos['productos']),
                'mensaje': f"Te recomiendo estos {len(productos['productos'])} productos"
            })
        
        elif intencion['tipo'] == 'categorias':
            # Listar categorías
            categorias = Categoria.query.all()
            categorias_data = [{'id': cat.id_categoria, 'nombre': cat.nombre} for cat in categorias]
            
            return jsonify({
                'success': True,
                'tipo': 'categorias',
                'categorias': categorias_data,
                'mensaje': f"Tenemos {len(categorias_data)} categorías disponibles"
            })
        
        elif intencion['tipo'] == 'precio':
            # Buscar por precio
            productos = buscar_productos_bot(
                precio_max=intencion.get('precio_max'),
                precio_min=intencion.get('precio_min'),
                query=intencion.get('query', '')
            )
            
            return jsonify({
                'success': True,
                'tipo': 'precio',
                'productos': productos,
                'total': len(productos),
                'mensaje': f"Encontré {len(productos)} producto(s) en ese rango de precio"
            })
        
        else:
            # Respuesta genérica
            return jsonify({
                'success': True,
                'tipo': 'ayuda',
                'mensaje': 'Puedo ayudarte a buscar productos, recomendar según tus necesidades, o mostrar categorías. ¿Qué necesitas?',
                'opciones': [
                    'Buscar productos específicos',
                    'Recomendaciones personalizadas',
                    'Ver categorías disponibles',
                    'Productos por precio'
                ]
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def detectar_intencion(mensaje):
    """Detecta la intención del usuario basándose en el mensaje"""
    intencion = {'tipo': 'ayuda'}
    
    # Detectar búsqueda
    if any(palabra in mensaje for palabra in ['buscar', 'busco', 'encontrar', 'quiero', 'necesito comprar']):
        intencion['tipo'] = 'buscar'
        # Extraer término de búsqueda
        palabras_busqueda = ['buscar', 'busco', 'encontrar', 'quiero', 'necesito comprar']
        query = mensaje
        for palabra in palabras_busqueda:
            query = query.replace(palabra, '').strip()
        intencion['query'] = query
        
        # Extraer precio si se menciona
        precio_match = re.search(r'(\d+)\s*(bs|bolivianos|bs\.)', mensaje, re.IGNORECASE)
        if precio_match:
            intencion['precio_max'] = precio_match.group(1)
    
    # Detectar recomendación
    elif any(palabra in mensaje for palabra in ['recomendar', 'recomendación', 'recomiéndame', 'mejor', 'sugerir']):
        intencion['tipo'] = 'recomendar'
        precio_match = re.search(r'(\d+)\s*(bs|bolivianos|bs\.)', mensaje, re.IGNORECASE)
        if precio_match:
            intencion['presupuesto'] = precio_match.group(1)
    
    # Detectar categorías
    elif any(palabra in mensaje for palabra in ['categoría', 'categoria', 'categorias', 'tipos']):
        intencion['tipo'] = 'categorias'
    
    # Detectar búsqueda por precio
    elif any(palabra in mensaje for palabra in ['precio', 'barato', 'económico', 'economico', 'caro', 'hasta']):
        intencion['tipo'] = 'precio'
        precio_match = re.search(r'(\d+)\s*(bs|bolivianos|bs\.)', mensaje, re.IGNORECASE)
        if precio_match:
            intencion['precio_max'] = precio_match.group(1)
        if 'barato' in mensaje or 'económico' in mensaje or 'economico' in mensaje:
            intencion['query'] = 'barato'
    
    return intencion

def buscar_productos_bot(query='', categoria=None, precio_max=None, precio_min=None):
    """Función auxiliar para buscar productos"""
    productos_query = Producto.query.filter_by(estado='activo')
    
    if query:
        productos_query = productos_query.filter(
            (Producto.nombre.ilike(f'%{query}%')) |
            (Producto.descripcion.ilike(f'%{query}%'))
        )
    
    if categoria:
        categoria_obj = Categoria.query.filter(
            Categoria.nombre.ilike(f'%{categoria}%')
        ).first()
        if categoria_obj:
            productos_query = productos_query.filter_by(id_categoria=categoria_obj.id_categoria)
    
    if precio_max:
        productos_query = productos_query.filter(Producto.precio <= float(precio_max))
    if precio_min:
        productos_query = productos_query.filter(Producto.precio >= float(precio_min))
    
    productos = productos_query.order_by(Producto.precio).limit(10).all()
    
    productos_data = []
    for producto in productos:
        productos_data.append({
            'id': producto.id_producto,
            'nombre': producto.nombre,
            'descripcion': producto.descripcion or 'Sin descripción',
            'precio': float(producto.precio),
            'stock': producto.stock,
            'categoria': producto.categoria.nombre if producto.categoria else 'Sin categoría',
            'url': url_for('producto', id=producto.id_producto)
        })
    
    return productos_data

def recomendar_productos_bot(necesidad='', presupuesto=None, uso=''):
    """Función auxiliar para recomendar productos"""
    necesidad_lower = necesidad.lower()
    
    categorias_keywords = {
        'smartphone': ['smartphone', 'celular', 'telefono', 'teléfono', 'móvil', 'movil', 'iphone', 'samsung', 'huawei'],
        'laptop': ['laptop', 'portatil', 'portátil', 'notebook', 'computadora', 'pc portatil', 'macbook'],
        'tablet': ['tablet', 'ipad', 'tableta'],
        'accesorio': ['accesorio', 'auricular', 'audifono', 'cargador', 'cable', 'case', 'funda', 'protector']
    }
    
    categoria_id = None
    categoria_nombre = None
    for cat_name, keywords in categorias_keywords.items():
        if any(keyword in necesidad_lower for keyword in keywords):
            categoria_obj = Categoria.query.filter(
                Categoria.nombre.ilike(f'%{cat_name}%')
            ).first()
            if categoria_obj:
                categoria_id = categoria_obj.id_categoria
                categoria_nombre = categoria_obj.nombre
                break
    
    productos_query = Producto.query.filter_by(estado='activo')
    
    if categoria_id:
        productos_query = productos_query.filter_by(id_categoria=categoria_id)
    
    if presupuesto:
        try:
            presupuesto_float = float(presupuesto)
            productos_query = productos_query.filter(Producto.precio <= presupuesto_float)
        except:
            pass
    
    if 'economico' in necesidad_lower or 'barato' in necesidad_lower or 'precio' in necesidad_lower:
        productos_query = productos_query.order_by(Producto.precio)
    elif 'mejor' in necesidad_lower or 'calidad' in necesidad_lower or 'premium' in necesidad_lower:
        productos_query = productos_query.order_by(Producto.precio.desc())
    else:
        productos_query = productos_query.order_by(Producto.stock.desc(), Producto.precio)
    
    productos = productos_query.limit(5).all()
    
    productos_data = []
    for producto in productos:
        productos_data.append({
            'id': producto.id_producto,
            'nombre': producto.nombre,
            'descripcion': producto.descripcion or 'Sin descripción',
            'precio': float(producto.precio),
            'stock': producto.stock,
            'categoria': producto.categoria.nombre if producto.categoria else 'Sin categoría',
            'url': url_for('producto', id=producto.id_producto)
        })
    
    return {
        'productos': productos_data,
        'categoria': categoria_nombre
    }

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 
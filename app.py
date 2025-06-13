from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from decimal import Decimal
from werkzeug.utils import secure_filename
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'clave_secreta_por_defecto')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql://root:@localhost/sistema_electronicos')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = './images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

# Asegurarse de que la carpeta de imágenes existe
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modelos
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    tipo_usuario = db.Column(db.Enum('admin', 'usuario'), nullable=False, default='usuario')
    direccion = db.Column(db.Text)
    telefono = db.Column(db.String(20))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_id(self):
        return str(self.id_usuario)
    
    def is_admin(self):
        return self.tipo_usuario == 'admin'

class Producto(db.Model):
    __tablename__ = 'productos'
    id_producto = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    id_categoria = db.Column(db.Integer, db.ForeignKey('categorias.id_categoria'))
    imagen = db.Column(db.String(255))
    estado = db.Column(db.String(20), default='activo')
    
    categoria = db.relationship('Categoria', backref=db.backref('productos', lazy=True))

class Categoria(db.Model):
    __tablename__ = 'categorias'
    id_categoria = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)

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
    fecha_pedido = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, nullable=True)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.Enum('pendiente', 'en_proceso', 'enviado', 'entregado', 'cancelado'), default='pendiente')
    direccion_envio = db.Column(db.String(200), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    metodo_pago = db.Column(db.String(50), nullable=True)
    
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

@app.before_request
def before_request():
    if current_user.is_authenticated:
        carrito_count = Carrito.query.filter_by(id_usuario=current_user.id_usuario).count()
        g.carrito_count = carrito_count
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
        total = sum(item.producto.precio * item.cantidad for item in items_carrito)
        return render_template('carrito.html', items=items_carrito, total=total)
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
        if not items:
            flash('El carrito está vacío')
            return redirect(url_for('carrito'))
        
        total = sum(item.producto.precio * item.cantidad for item in items)
        
        pedido = Pedido(
            id_usuario=current_user.id_usuario,
            total=total,
            direccion_envio=direccion,
            telefono=current_user.telefono,
            estado='pendiente',
            metodo_pago=metodo_pago
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
        
        Carrito.query.filter_by(id_usuario=current_user.id_usuario).delete()
        db.session.commit()
        
        flash('Pedido realizado con éxito')
        return redirect(url_for('user_dashboard'))
    
    items = Carrito.query.filter_by(id_usuario=current_user.id_usuario).all()
    total = sum(item.producto.precio * item.cantidad for item in items)
    return render_template('checkout.html', items=items, total=total)

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        password = request.form.get('password')
        direccion = request.form.get('direccion')
        telefono = request.form.get('telefono')
        
        if Usuario.query.filter_by(email=email).first():
            flash('El email ya está registrado.', 'danger')
            return redirect(url_for('registro'))
        
        # Generar hash de la contraseña
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        nuevo_usuario = Usuario(
            nombre=nombre,
            email=email,
            password=hashed_password,
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
            flash('Error al registrar usuario.', 'danger')
    
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = Usuario.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('¡Bienvenido!', 'success')
            
            if user.is_admin():
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Email o contraseña incorrectos.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.tipo_usuario != 'admin':
        flash('No tienes permiso para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    try:
        # Obtener estadísticas
        total_ventas = db.session.query(func.sum(Pedido.total)).filter(Pedido.estado != 'cancelado').scalar() or 0
        pedidos_pendientes = Pedido.query.filter_by(estado='pendiente').count()
        total_usuarios = Usuario.query.filter_by(tipo_usuario='cliente').count()
        total_productos = Producto.query.count()
        
        # Obtener pedidos pendientes
        pedidos = Pedido.query.filter_by(estado='pendiente').order_by(Pedido.fecha_pedido.desc()).all()
        
        return render_template('admin/dashboard.html',
                             total_ventas=total_ventas,
                             pedidos_pendientes=pedidos_pendientes,
                             total_usuarios=total_usuarios,
                             total_productos=total_productos,
                             pedidos=pedidos)
    except Exception as e:
        flash('Error al cargar el dashboard', 'error')
        print(f"Error: {str(e)}")  # Para debugging
        return redirect(url_for('index'))

@app.route('/admin/productos')
@login_required
def admin_productos():
    if current_user.tipo_usuario != 'admin':
        flash('No tienes permiso para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    try:
        productos = Producto.query.all()
        return render_template('admin/productos.html', productos=productos)
    except Exception as e:
        flash('Error al cargar los productos', 'error')
        print(f"Error: {str(e)}")  # Para debugging
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/usuarios')
@login_required
def admin_usuarios():
    if current_user.tipo_usuario != 'admin':
        flash('No tienes permiso para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    try:
        usuarios = Usuario.query.filter_by(tipo_usuario='usuario').all()
        return render_template('admin/usuarios.html', usuarios=usuarios)
    except Exception as e:
        flash('Error al cargar los usuarios', 'error')
        print(f"Error: {str(e)}")  # Para debugging
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/producto/agregar', methods=['GET', 'POST'])
@login_required
def agregar_producto():
    if current_user.tipo_usuario != 'admin':
        flash('No tienes permiso para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    try:
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion')
            precio = float(request.form.get('precio'))
            stock = int(request.form.get('stock'))
            id_categoria = int(request.form.get('categoria'))
            
            imagen = request.files.get('imagen')
            if imagen:
                filename = secure_filename(imagen.filename)
                imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen_path = filename
            else:
                imagen_path = None
            
            producto = Producto(
                nombre=nombre,
                descripcion=descripcion,
                precio=precio,
                stock=stock,
                id_categoria=id_categoria,
                imagen=imagen_path
            )
            
            db.session.add(producto)
            db.session.commit()
            flash('Producto agregado exitosamente', 'success')
            return redirect(url_for('admin_productos'))
        
        categorias = Categoria.query.all()
        return render_template('admin/agregar_producto.html', categorias=categorias)
    except Exception as e:
        db.session.rollback()
        flash('Error al agregar el producto', 'error')
        print(f"Error: {str(e)}")  # Para debugging
        return redirect(url_for('admin_productos'))

@app.route('/admin/producto/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_producto(id):
    if not current_user.is_admin():
        return redirect(url_for('index'))
    
    producto = Producto.query.get_or_404(id)
    
    if request.method == 'POST':
        producto.nombre = request.form.get('nombre')
        producto.descripcion = request.form.get('descripcion')
        producto.precio = float(request.form.get('precio'))
        producto.stock = int(request.form.get('stock'))
        producto.id_categoria = int(request.form.get('categoria'))
        
        imagen = request.files.get('imagen')
        if imagen:
            filename = secure_filename(imagen.filename)
            imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            producto.imagen = filename
        
        db.session.commit()
        flash('Producto actualizado exitosamente')
        return redirect(url_for('admin_dashboard'))
    
    categorias = Categoria.query.all()
    return render_template('admin/editar_producto.html', producto=producto, categorias=categorias)

@app.route('/admin/producto/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_producto(id):
    if not current_user.is_admin():
        return redirect(url_for('index'))
    
    producto = Producto.query.get_or_404(id)
    producto.estado = 'inactivo'
    db.session.commit()
    flash('Producto eliminado exitosamente')
    return redirect(url_for('admin_dashboard'))

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    pedidos = Pedido.query.filter_by(id_usuario=current_user.id_usuario).all()
    return render_template('user/dashboard.html', pedidos=pedidos)

@app.route('/actualizar_perfil', methods=['POST'])
@login_required
def actualizar_perfil():
    if request.method == 'POST':
        current_user.nombre = request.form.get('nombre')
        current_user.email = request.form.get('email')
        current_user.telefono = request.form.get('telefono')
        current_user.direccion = request.form.get('direccion')
        
        db.session.commit()
        flash('Perfil actualizado exitosamente')
        return redirect(url_for('user_dashboard'))

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
def ver_pedido_admin(id):
    if current_user.tipo_usuario != 'admin':
        flash('No tienes permiso para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    try:
        pedido = Pedido.query.get_or_404(id)
        return render_template('admin/ver_pedido.html', pedido=pedido)
    except Exception as e:
        flash('Error al cargar los detalles del pedido', 'error')
        print(f"Error: {str(e)}")  # Para debugging
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/pedido/estado/<int:id>', methods=['POST'])
@login_required
def actualizar_estado_pedido(id):
    if current_user.tipo_usuario != 'admin':
        flash('No tienes permiso para realizar esta acción', 'error')
        return redirect(url_for('index'))
    
    try:
        pedido = Pedido.query.get_or_404(id)
        nuevo_estado = request.form.get('estado')
        
        if nuevo_estado not in ['pendiente', 'en_proceso', 'enviado', 'entregado', 'cancelado']:
            flash('Estado no válido', 'error')
            return redirect(url_for('ver_pedido_admin', id=id))
        
        pedido.estado = nuevo_estado
        pedido.fecha_actualizacion = datetime.utcnow()
        db.session.commit()
        
        flash(f'Estado del pedido actualizado a {nuevo_estado.replace("_", " ").title()}', 'success')
        return redirect(url_for('ver_pedido_admin', id=id))
    except Exception as e:
        db.session.rollback()
        flash('Error al actualizar el estado del pedido', 'error')
        print(f"Error: {str(e)}")  # Para debugging
        return redirect(url_for('ver_pedido_admin', id=id))

@app.route('/admin/usuario/editar/<int:id>', methods=['GET', 'POST'])
@login_required
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
def eliminar_usuario(id):
    if not current_user.is_admin():
        flash('No tienes permiso para realizar esta acción.', 'danger')
        return redirect(url_for('index'))
    
    if id == current_user.id_usuario:
        flash('No puedes eliminar tu propia cuenta.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    usuario = Usuario.query.get_or_404(id)
    
    try:
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuario eliminado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar el usuario.', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/carrito/procesar', methods=['POST'])
@login_required
def procesar_pedido():
    try:
        # Obtener items del carrito
        items = Carrito.query.filter_by(id_usuario=current_user.id_usuario).all()
        if not items:
            flash('El carrito está vacío', 'error')
            return redirect(url_for('carrito'))
        
        # Calcular total
        total = sum(item.producto.precio * item.cantidad for item in items)
        
        # Crear el pedido
        pedido = Pedido(
            id_usuario=current_user.id_usuario,
            total=total,
            estado='pendiente',
            direccion_envio=current_user.direccion,
            telefono=current_user.telefono
        )
        db.session.add(pedido)
        db.session.flush()  # Para obtener el ID del pedido
        
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
                flash('Stock insuficiente para algunos productos', 'error')
                return redirect(url_for('carrito'))
        
        # Limpiar el carrito
        Carrito.query.filter_by(id_usuario=current_user.id_usuario).delete()
        
        # Guardar cambios
        db.session.commit()
        
        # Notificar al administrador
        admin = Usuario.query.filter_by(tipo_usuario='admin').first()
        if admin:
            flash(f'Pedido #{pedido.id_pedido} realizado con éxito. El administrador será notificado.', 'success')
        else:
            flash('Pedido realizado con éxito', 'success')
        
        return redirect(url_for('user_dashboard'))
    except Exception as e:
        db.session.rollback()
        flash('Error al procesar el pedido', 'error')
        print(f"Error: {str(e)}")  # Para debugging
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 
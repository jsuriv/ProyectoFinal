-- Actualización de la base de datos para ElectroWorld
-- Agregar nueva categoría de servicios de mantenimiento

USE sistema_electronicos;

-- Insertar nueva categoría para servicios de mantenimiento
INSERT INTO categorias (nombre, descripcion, estado, fecha_creacion) VALUES
('Servicios de Mantenimiento', 'Servicios profesionales de mantenimiento, reparación y soporte técnico para dispositivos electrónicos', 'activo', NOW());

-- Obtener el ID de la nueva categoría
SET @categoria_mantenimiento_id = LAST_INSERT_ID();

-- Insertar productos de servicios de mantenimiento
INSERT INTO productos (nombre, descripcion, precio, stock, id_categoria, imagen, estado, fecha_creacion) VALUES
('Mantenimiento de Laptop', 'Servicio completo de mantenimiento preventivo y correctivo para laptops. Incluye limpieza interna, cambio de pasta térmica, optimización del sistema y diagnóstico completo.', 150.00, 999, @categoria_mantenimiento_id, 'mantenimiento_laptop.jpg', 'activo', NOW()),

('Reparación de Smartphone', 'Reparación profesional de smartphones y tablets. Incluye cambio de pantalla, batería, reparación de software y recuperación de datos.', 200.00, 999, @categoria_mantenimiento_id, 'reparacion_smartphone.jpg', 'activo', NOW()),

('Reparación de PC', 'Ensamblaje, actualización y reparación de computadoras de escritorio. Incluye instalación de software y diagnóstico de problemas.', 100.00, 999, @categoria_mantenimiento_id, 'reparacion_pc.jpg', 'activo', NOW()),

('Seguridad Informática', 'Protección completa de dispositivos contra malware y amenazas. Incluye instalación de antivirus, limpieza de malware y configuración de firewall.', 80.00, 999, @categoria_mantenimiento_id, 'seguridad_informatica.jpg', 'activo', NOW()),

('Configuración de Redes', 'Configuración y reparación de redes WiFi y conexiones de internet. Incluye optimización de red e instalación de routers.', 120.00, 999, @categoria_mantenimiento_id, 'configuracion_redes.jpg', 'activo', NOW()),

('Recuperación de Datos', 'Servicio especializado en recuperación de datos perdidos o eliminados de dispositivos electrónicos.', 250.00, 999, @categoria_mantenimiento_id, 'recuperacion_datos.jpg', 'activo', NOW()),

('Instalación de Software', 'Instalación y configuración de software especializado, sistemas operativos y aplicaciones de productividad.', 60.00, 999, @categoria_mantenimiento_id, 'instalacion_software.jpg', 'activo', NOW()),

('Actualización de Hardware', 'Actualización de componentes de computadora para mejorar el rendimiento y funcionalidad.', 180.00, 999, @categoria_mantenimiento_id, 'actualizacion_hardware.jpg', 'activo', NOW());

-- Crear tabla para servicios de mantenimiento
CREATE TABLE IF NOT EXISTS servicios_mantenimiento (
    id_servicio INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10,2) NOT NULL,
    duracion_estimada VARCHAR(50),
    garantia_dias INT DEFAULT 30,
    categoria_servicio ENUM('laptop', 'smartphone', 'pc', 'redes', 'seguridad', 'otros') NOT NULL,
    estado ENUM('activo', 'inactivo') DEFAULT 'activo',
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insertar servicios en la nueva tabla
INSERT INTO servicios_mantenimiento (nombre, descripcion, precio, duracion_estimada, garantia_dias, categoria_servicio) VALUES
('Limpieza Profunda de Laptop', 'Limpieza interna completa, cambio de pasta térmica y optimización del sistema', 150.00, '2-3 horas', 90, 'laptop'),
('Cambio de Pantalla Smartphone', 'Reemplazo de pantalla rota con repuesto original y garantía', 200.00, '1-2 horas', 180, 'smartphone'),
('Ensamblaje de PC Gaming', 'Ensamblaje completo de computadora gaming con componentes de alta calidad', 300.00, '4-6 horas', 365, 'pc'),
('Configuración de Red WiFi', 'Configuración completa de red WiFi para hogar o empresa', 120.00, '1-2 horas', 60, 'redes'),
('Limpieza de Malware', 'Eliminación completa de virus, spyware y malware del sistema', 80.00, '2-4 horas', 30, 'seguridad'),
('Recuperación de Datos', 'Recuperación de archivos perdidos o eliminados accidentalmente', 250.00, '24-48 horas', 90, 'otros'),
('Instalación de Windows', 'Instalación limpia de Windows con drivers y software básico', 60.00, '2-3 horas', 30, 'pc'),
('Actualización de RAM', 'Instalación de memoria RAM adicional para mejorar rendimiento', 180.00, '1 hora', 90, 'pc');

-- Crear tabla para solicitudes de servicio
CREATE TABLE IF NOT EXISTS solicitudes_servicio (
    id_solicitud INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    id_servicio INT NOT NULL,
    descripcion_problema TEXT NOT NULL,
    marca_modelo VARCHAR(100),
    fecha_solicitud DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_agendada DATETIME,
    estado ENUM('pendiente', 'confirmada', 'en_proceso', 'completada', 'cancelada') DEFAULT 'pendiente',
    precio_final DECIMAL(10,2),
    observaciones TEXT,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_servicio) REFERENCES servicios_mantenimiento(id_servicio) ON DELETE CASCADE
);

-- Crear tabla para historial de servicios
CREATE TABLE IF NOT EXISTS historial_servicios (
    id_historial INT AUTO_INCREMENT PRIMARY KEY,
    id_solicitud INT NOT NULL,
    id_tecnico INT,
    fecha_inicio DATETIME,
    fecha_fin DATETIME,
    trabajo_realizado TEXT,
    repuestos_utilizados TEXT,
    costo_repuestos DECIMAL(10,2) DEFAULT 0.00,
    tiempo_total_horas DECIMAL(4,2),
    calidad_servicio ENUM('excelente', 'bueno', 'regular', 'malo'),
    comentarios_cliente TEXT,
    FOREIGN KEY (id_solicitud) REFERENCES solicitudes_servicio(id_solicitud) ON DELETE CASCADE,
    FOREIGN KEY (id_tecnico) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
);

-- Agregar índices para mejorar el rendimiento
CREATE INDEX idx_servicios_categoria ON servicios_mantenimiento(categoria_servicio);
CREATE INDEX idx_solicitudes_usuario ON solicitudes_servicio(id_usuario);
CREATE INDEX idx_solicitudes_estado ON solicitudes_servicio(estado);
CREATE INDEX idx_historial_solicitud ON historial_servicios(id_solicitud);

-- Actualizar la descripción de la empresa en la base de datos
-- (Esto se puede hacer manualmente en la aplicación)

COMMIT;

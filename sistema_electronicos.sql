-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 13-06-2025 a las 18:06:08
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `sistema_electronicos`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `acciones_admin`
--

CREATE TABLE `acciones_admin` (
  `id_accion` int(11) NOT NULL,
  `id_pedido` int(11) NOT NULL,
  `id_admin` int(11) NOT NULL,
  `tipo_accion` enum('actualizar_estado','emitir_factura','anular_pedido','actualizar_factura') NOT NULL,
  `descripcion` text DEFAULT NULL,
  `fecha_accion` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `acciones_admin`
--

INSERT INTO `acciones_admin` (`id_accion`, `id_pedido`, `id_admin`, `tipo_accion`, `descripcion`, `fecha_accion`) VALUES
(1, 2, 2, 'actualizar_estado', 'Estado cambiado de pendiente a en_proceso', '2025-06-13 12:02:55'),
(2, 1, 4, 'actualizar_estado', 'Estado cambiado de pendiente a enviado', '2025-06-13 12:03:01');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `carrito`
--

CREATE TABLE `carrito` (
  `id_carrito` int(11) NOT NULL,
  `id_usuario` int(11) NOT NULL,
  `id_producto` int(11) NOT NULL,
  `cantidad` int(11) NOT NULL DEFAULT 1,
  `fecha_agregado` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `carrito`
--

INSERT INTO `carrito` (`id_carrito`, `id_usuario`, `id_producto`, `cantidad`, `fecha_agregado`) VALUES
(6, 4, 1, 1, '2025-06-13 15:54:24'),
(7, 4, 2, 1, '2025-06-13 15:54:28');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `categorias`
--

CREATE TABLE `categorias` (
  `id_categoria` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `estado` varchar(20) DEFAULT 'activo',
  `fecha_creacion` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `categorias`
--

INSERT INTO `categorias` (`id_categoria`, `nombre`, `descripcion`, `estado`, `fecha_creacion`) VALUES
(1, 'Smartphones', 'Teléfonos móviles de última generación', 'activo', '2025-06-13 15:19:48'),
(2, 'Laptops', 'Computadoras portátiles para trabajo y gaming', 'activo', '2025-06-13 15:19:48'),
(3, 'Tablets', 'Dispositivos táctiles para productividad y entretenimiento', 'activo', '2025-06-13 15:19:48'),
(4, 'Accesorios', 'Complementos y accesorios para dispositivos electrónicos', 'activo', '2025-06-13 15:19:48');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `detalles_pedido`
--

CREATE TABLE `detalles_pedido` (
  `id_detalle` int(11) NOT NULL,
  `id_pedido` int(11) NOT NULL,
  `id_producto` int(11) NOT NULL,
  `cantidad` int(11) NOT NULL,
  `precio_unitario` decimal(10,2) NOT NULL,
  `subtotal` decimal(10,2) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `detalles_pedido`
--

INSERT INTO `detalles_pedido` (`id_detalle`, `id_pedido`, `id_producto`, `cantidad`, `precio_unitario`, `subtotal`) VALUES
(1, 1, 1, 3, 999.99, 2999.97),
(2, 2, 1, 8, 999.99, 7999.92);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `estados_factura`
--

CREATE TABLE `estados_factura` (
  `id_estado` int(11) NOT NULL,
  `id_factura` int(11) NOT NULL,
  `estado` enum('pendiente','emitida','anulada','reimpresa') NOT NULL,
  `fecha_cambio` datetime DEFAULT current_timestamp(),
  `id_admin` int(11) DEFAULT NULL,
  `observacion` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `estados_factura`
--

INSERT INTO `estados_factura` (`id_estado`, `id_factura`, `estado`, `fecha_cambio`, `id_admin`, `observacion`) VALUES
(1, 1, 'pendiente', '2025-06-13 11:20:08', NULL, 'Factura creada automáticamente'),
(2, 2, 'pendiente', '2025-06-13 11:48:50', NULL, 'Factura creada automáticamente');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `facturas`
--

CREATE TABLE `facturas` (
  `id_factura` int(11) NOT NULL,
  `id_pedido` int(11) NOT NULL,
  `numero_factura` varchar(20) NOT NULL,
  `voucher_number` varchar(20) NOT NULL,
  `fecha_emision` datetime DEFAULT current_timestamp(),
  `subtotal` decimal(10,2) NOT NULL DEFAULT 0.00,
  `iva` decimal(10,2) NOT NULL DEFAULT 0.00,
  `total` decimal(10,2) NOT NULL DEFAULT 0.00,
  `estado` enum('emitida','anulada') DEFAULT 'emitida',
  `pdf_path` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `facturas`
--

INSERT INTO `facturas` (`id_factura`, `id_pedido`, `numero_factura`, `voucher_number`, `fecha_emision`, `subtotal`, `iva`, `total`, `estado`, `pdf_path`) VALUES
(1, 1, 'FACT-000001', 'VOU-20250613-000001', '2025-06-13 11:20:08', 2999.97, 390.00, 3389.97, 'emitida', 'C:\\xampp\\htdocs\\ProyectoFinal\\static\\facturas\\factura_FACT-000001.pdf'),
(2, 2, 'FACT-000002', 'VOU-20250613-000002', '2025-06-13 11:48:50', 0.00, 0.00, 7999.92, 'emitida', 'C:\\xampp\\htdocs\\ProyectoFinal\\static\\facturas\\factura_FACT-000002.pdf');

--
-- Disparadores `facturas`
--
DELIMITER $$
CREATE TRIGGER `after_factura_insert` AFTER INSERT ON `facturas` FOR EACH ROW BEGIN
    -- Insertar estado inicial de la factura
    INSERT INTO estados_factura (id_factura, estado, observacion)
    VALUES (NEW.id_factura, 'pendiente', 'Factura creada automáticamente');
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `usuarios`
--

CREATE TABLE `usuarios` (
  `id_usuario` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `tipo_usuario` enum('admin','usuario') NOT NULL DEFAULT 'usuario',
  `nit` varchar(20) DEFAULT NULL,
  `direccion` varchar(255) DEFAULT NULL,
  `telefono` varchar(20) DEFAULT NULL,
  `estado` enum('activo','inactivo') NOT NULL DEFAULT 'activo',
  `fecha_registro` datetime DEFAULT current_timestamp(),
  `paypal_email` varchar(255) DEFAULT NULL,
  `paypal_verified` boolean DEFAULT FALSE,
  `paypal_verification_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id_usuario`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `usuarios`
--

INSERT INTO `usuarios` (
    `id_usuario`, 
    `nombre`, 
    `email`, 
    `password`, 
    `tipo_usuario`, 
    `nit`, 
    `direccion`, 
    `telefono`, 
    `estado`, 
    `fecha_registro`, 
    `paypal_email`, 
    `paypal_verified`, 
    `paypal_verification_date`
) VALUES
(2, 'Jhonathan', 'jhonn@gmail.com', 'pbkdf2:sha256:600000$rHe1G8eohPxKcHlz$92e7bce188a79194f9936b8f695711d5c19d04e0b0cec1395660a043f8efacbe', 'admin', NULL, 'Aniceto Arce 46', '75781303', 'activo', '2025-06-13 07:30:21', NULL, FALSE, NULL),
(4, 'juanjo', 'juanjo@gmail.com', 'pbkdf2:sha256:600000$d9D8sNtJojwcVmDP$a1c6d816e773310c9ff47acfe6b2655253ef2171f6f5c876f09d2d31f275e3d4', 'usuario', NULL, 'lomaspampas', '456767678', 'activo', '2025-06-13 07:38:29', NULL, FALSE, NULL),
(5, 'pepe', 'pepe@gmail.com', 'pbkdf2:sha256:600000$6Tmw4NTkx01cfwWU$1360e0505b9e4feb2d5aa5f2c54e022026171fc7a9c59dbf57a5bc46f8b71c6f', 'usuario', '12345678912', 'feliz morales #66', '74440011', 'activo', '2025-06-13 16:01:23', NULL, FALSE, NULL);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `pedidos`
--

CREATE TABLE `pedidos` (
  `id_pedido` int(11) NOT NULL AUTO_INCREMENT,
  `id_usuario` int(11) NOT NULL,
  `numero_factura` varchar(20) NOT NULL,
  `fecha_pedido` datetime NOT NULL,
  `fecha_actualizacion` datetime NOT NULL,
  `subtotal` decimal(10,2) NOT NULL,
  `iva` decimal(10,2) NOT NULL,
  `total` decimal(10,2) NOT NULL,
  `estado` enum('pendiente','en_proceso','enviado','entregado','cancelado') NOT NULL DEFAULT 'pendiente',
  `direccion_envio` varchar(255) NOT NULL,
  `telefono` varchar(20) NOT NULL,
  `metodo_pago` varchar(50) DEFAULT 'efectivo',
  `paypal_payment_id` varchar(255) DEFAULT NULL,
  `paypal_payer_id` varchar(255) DEFAULT NULL,
  `paypal_payment_status` varchar(50) DEFAULT NULL,
  `paypal_payment_date` datetime DEFAULT NULL,
  `paypal_transaction_id` varchar(255) DEFAULT NULL,
  `paypal_payment_method` varchar(50) DEFAULT 'paypal',
  `paypal_payment_currency` varchar(10) DEFAULT 'USD',
  `paypal_payment_amount` decimal(10,2) DEFAULT NULL,
  `paypal_payment_fee` decimal(10,2) DEFAULT NULL,
  `paypal_payment_tax` decimal(10,2) DEFAULT NULL,
  `paypal_payment_shipping` decimal(10,2) DEFAULT NULL,
  `paypal_payment_subtotal` decimal(10,2) DEFAULT NULL,
  `paypal_payment_total` decimal(10,2) DEFAULT NULL,
  `paypal_payment_created_at` datetime DEFAULT NULL,
  `paypal_payment_updated_at` datetime DEFAULT NULL,
  `paypal_payment_error` text DEFAULT NULL,
  PRIMARY KEY (`id_pedido`),
  KEY `id_usuario` (`id_usuario`),
  CONSTRAINT `pedidos_ibfk_1` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuario`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `pedidos`
--

INSERT INTO `pedidos` (
    `id_pedido`, 
    `id_usuario`, 
    `numero_factura`, 
    `fecha_pedido`, 
    `fecha_actualizacion`, 
    `subtotal`, 
    `iva`, 
    `total`, 
    `estado`, 
    `direccion_envio`, 
    `telefono`, 
    `metodo_pago`, 
    `paypal_payment_id`, 
    `paypal_payer_id`, 
    `paypal_payment_status`, 
    `paypal_payment_date`, 
    `paypal_transaction_id`, 
    `paypal_payment_method`, 
    `paypal_payment_currency`, 
    `paypal_payment_amount`, 
    `paypal_payment_fee`, 
    `paypal_payment_tax`, 
    `paypal_payment_shipping`, 
    `paypal_payment_subtotal`, 
    `paypal_payment_total`, 
    `paypal_payment_created_at`, 
    `paypal_payment_updated_at`, 
    `paypal_payment_error`
) VALUES
(1, 4, 'FACT-000001', '2025-06-13 15:20:08', '2025-06-13 16:03:01', 2654.84, 345.13, 2999.97, 'enviado', 'lomaspampas', '456767678', 'paypal', NULL, NULL, NULL, NULL, NULL, 'paypal', 'USD', 2999.97, NULL, 345.13, NULL, 2654.84, 2999.97, '2025-06-13 15:20:08', '2025-06-13 16:03:01', NULL),
(2, 2, 'FACT-000002', '2025-06-13 15:48:50', '2025-06-13 16:02:55', 7079.58, 920.34, 7999.92, 'en_proceso', 'Aniceto Arce 46', '75781303', 'paypal', NULL, NULL, NULL, NULL, NULL, 'paypal', 'USD', 7999.92, NULL, 920.34, NULL, 7079.58, 7999.92, '2025-06-13 15:48:50', '2025-06-13 16:02:55', NULL);

--
-- Disparadores `pedidos`
--
DELIMITER $$
CREATE TRIGGER `after_pedido_insert` AFTER INSERT ON `pedidos` FOR EACH ROW BEGIN
    INSERT INTO facturas (id_pedido, numero_factura, subtotal, iva, total)
    VALUES (NEW.id_pedido, NEW.numero_factura, NEW.subtotal, NEW.iva, NEW.total);
END
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `after_pedido_status_update` AFTER UPDATE ON `pedidos` FOR EACH ROW BEGIN
    IF OLD.estado != NEW.estado THEN
        INSERT INTO acciones_admin (id_pedido, id_admin, tipo_accion, descripcion)
        VALUES (NEW.id_pedido, NEW.id_usuario, 'actualizar_estado', 
                CONCAT('Estado cambiado de ', OLD.estado, ' a ', NEW.estado));
    END IF;
END
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `after_pedido_update` AFTER UPDATE ON `pedidos` FOR EACH ROW BEGIN
    UPDATE facturas 
    SET subtotal = NEW.subtotal,
        iva = NEW.iva,
        total = NEW.total
    WHERE id_pedido = NEW.id_pedido;
END
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `before_pedido_insert` BEFORE INSERT ON `pedidos` FOR EACH ROW BEGIN
    DECLARE next_id INT;
    SELECT COALESCE(MAX(id_pedido), 0) + 1 INTO next_id FROM pedidos;
    SET NEW.numero_factura = CONCAT('FACT-', LPAD(next_id, 6, '0'));
    
    -- Asegurar que los campos numéricos no sean nulos
    IF NEW.subtotal IS NULL THEN
        SET NEW.subtotal = 0.00;
    END IF;
    IF NEW.iva IS NULL THEN
        SET NEW.iva = 0.00;
    END IF;
    IF NEW.total IS NULL THEN
        SET NEW.total = NEW.subtotal + NEW.iva;
    END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `productos`
--

CREATE TABLE `productos` (
  `id_producto` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `precio` float NOT NULL,
  `stock` int(11) NOT NULL,
  `id_categoria` int(11) DEFAULT NULL,
  `imagen` varchar(255) DEFAULT NULL,
  `estado` varchar(20) DEFAULT 'activo',
  `fecha_creacion` datetime DEFAULT current_timestamp(),
  `fecha_actualizacion` datetime DEFAULT NULL ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `productos`
--

INSERT INTO `productos` (`id_producto`, `nombre`, `descripcion`, `precio`, `stock`, `id_categoria`, `imagen`, `estado`, `fecha_creacion`, `fecha_actualizacion`) VALUES
(1, 'iPhone 15 Pro', 'El último iPhone con chip A17 Pro y cámara de 48MP.', 999.99, 39, 1, 'iphone15pro.jpg', 'activo', '2025-06-13 15:19:48', '2025-06-13 15:48:50'),
(2, 'Samsung Galaxy S24 Ultra', 'Potencia y versatilidad con S Pen incluido.', 1199.99, 40, 1, 's24ultra.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(3, 'Google Pixel 8 Pro', 'La mejor cámara en un smartphone Android.', 899.99, 35, 1, 'pixel8pro.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(4, 'Xiaomi 14 Pro', 'Rendimiento premium a un precio competitivo.', 799.99, 45, 1, 'xiaomi14pro.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(5, 'OnePlus 12', 'Carga rápida y rendimiento excepcional.', 699.99, 30, 1, 'oneplus12.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(6, 'MacBook Pro M3', 'Potencia profesional con chip M3 y pantalla Liquid Retina XDR.', 1999.99, 25, 2, 'macbookprom3.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(7, 'Dell XPS 15', 'Diseño premium con pantalla OLED y procesador Intel Core i9.', 1799.99, 20, 2, 'dellxps15.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(8, 'Lenovo ThinkPad X1', 'Laptop empresarial con seguridad avanzada y gran duración de batería.', 1599.99, 30, 2, 'thinkpadx1.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(9, 'ASUS ROG Zephyrus', 'Laptop gaming con RTX 4090 y pantalla de 240Hz.', 2499.99, 15, 2, 'rogzephyrus.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(10, 'HP Spectre x360', 'Convertible premium con pantalla táctil y diseño elegante.', 1299.99, 25, 2, 'spectrex360.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(11, 'iPad Pro M2', 'Potencia profesional en formato tablet con pantalla Liquid Retina.', 899.99, 40, 3, 'ipadpro.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(12, 'Samsung Galaxy Tab S9 Ultra', 'Tablet Android premium con S Pen y pantalla AMOLED.', 799.99, 35, 3, 'tabs9ultra.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(13, 'Microsoft Surface Pro 9', 'Tablet convertible con Windows 11 y teclado desmontable.', 999.99, 30, 3, 'surfacepro9.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(14, 'Lenovo Tab P12 Pro', 'Tablet Android con pantalla OLED y altavoces JBL.', 599.99, 25, 3, 'tabp12pro.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(15, 'Xiaomi Pad 6 Pro', 'Tablet de gama alta con carga rápida y gran batería.', 499.99, 40, 3, 'pad6pro.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(16, 'AirPods Pro 2', 'Auriculares inalámbricos con cancelación activa de ruido.', 249.99, 100, 4, 'airpodspro2.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(17, 'Samsung Galaxy Watch 6', 'Smartwatch con monitor de salud avanzado y diseño elegante.', 299.99, 50, 4, 'galaxywatch6.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(18, 'Logitech MX Master 3S', 'Ratón premium para productividad con scroll electromagnético.', 99.99, 75, 4, 'mxmaster3s.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(19, 'Samsung 49\" Odyssey G9', 'Monitor gaming curvo con resolución 5120x1440 y 240Hz.', 999.99, 20, 4, 'odysseyg9.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(20, 'Apple Magic Keyboard', 'Teclado inalámbrico con diseño minimalista y gran duración de batería.', 149.99, 60, 4, 'magickeyboard.jpg', 'activo', '2025-06-13 15:19:48', NULL),
(21, 'samsumgs25ultra', 'samsumgs25ulta', 999, 2000, 1, 'samsumgs25ultra.jpg', 'activo', '2025-06-13 15:31:10', '2025-06-13 15:44:00');

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `acciones_admin`
--
ALTER TABLE `acciones_admin`
  ADD PRIMARY KEY (`id_accion`),
  ADD KEY `idx_pedido` (`id_pedido`),
  ADD KEY `idx_admin` (`id_admin`);

--
-- Indices de la tabla `carrito`
--
ALTER TABLE `carrito`
  ADD PRIMARY KEY (`id_carrito`),
  ADD KEY `idx_usuario` (`id_usuario`),
  ADD KEY `idx_producto` (`id_producto`);

--
-- Indices de la tabla `categorias`
--
ALTER TABLE `categorias`
  ADD PRIMARY KEY (`id_categoria`),
  ADD UNIQUE KEY `nombre` (`nombre`);

--
-- Indices de la tabla `detalles_pedido`
--
ALTER TABLE `detalles_pedido`
  ADD PRIMARY KEY (`id_detalle`),
  ADD KEY `idx_pedido` (`id_pedido`),
  ADD KEY `idx_producto` (`id_producto`);

--
-- Indices de la tabla `estados_factura`
--
ALTER TABLE `estados_factura`
  ADD PRIMARY KEY (`id_estado`),
  ADD KEY `idx_factura` (`id_factura`),
  ADD KEY `idx_admin` (`id_admin`);

--
-- Indices de la tabla `facturas`
--
ALTER TABLE `facturas`
  ADD PRIMARY KEY (`id_factura`),
  ADD UNIQUE KEY `numero_factura` (`numero_factura`),
  ADD KEY `idx_pedido` (`id_pedido`);

--
-- Indices de la tabla `pedidos`
--

--
-- Indices de la tabla `productos`
--
ALTER TABLE `productos`
  ADD PRIMARY KEY (`id_producto`),
  ADD KEY `idx_categoria` (`id_categoria`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `acciones_admin`
--
ALTER TABLE `acciones_admin`
  MODIFY `id_accion` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `carrito`
--
ALTER TABLE `carrito`
  MODIFY `id_carrito` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT de la tabla `categorias`
--
ALTER TABLE `categorias`
  MODIFY `id_categoria` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de la tabla `detalles_pedido`
--
ALTER TABLE `detalles_pedido`
  MODIFY `id_detalle` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `estados_factura`
--
ALTER TABLE `estados_factura`
  MODIFY `id_estado` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `facturas`
--
ALTER TABLE `facturas`
  MODIFY `id_factura` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `pedidos`
--
ALTER TABLE `pedidos`
  MODIFY `id_pedido` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `productos`
--
ALTER TABLE `productos`
  MODIFY `id_producto` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=22;

--
-- AUTO_INCREMENT de la tabla `usuarios`
--
ALTER TABLE `usuarios`
  MODIFY `id_usuario` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `acciones_admin`
--
ALTER TABLE `acciones_admin`
  ADD CONSTRAINT `fk_accion_admin` FOREIGN KEY (`id_admin`) REFERENCES `usuarios` (`id_usuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_accion_pedido` FOREIGN KEY (`id_pedido`) REFERENCES `pedidos` (`id_pedido`) ON DELETE CASCADE;

--
-- Filtros para la tabla `carrito`
--
ALTER TABLE `carrito`
  ADD CONSTRAINT `fk_carrito_producto` FOREIGN KEY (`id_producto`) REFERENCES `productos` (`id_producto`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_carrito_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuario`) ON DELETE CASCADE;

--
-- Filtros para la tabla `detalles_pedido`
--
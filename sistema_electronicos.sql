-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 13-06-2025 a las 06:17:30
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
-- Estructura de tabla para la tabla `carrito`
--

CREATE TABLE IF NOT EXISTS `carrito` (
  `id_carrito` int(11) NOT NULL AUTO_INCREMENT,
  `id_usuario` int(11) NOT NULL,
  `id_producto` int(11) NOT NULL,
  `cantidad` int(11) NOT NULL DEFAULT 1,
  `fecha_agregado` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_carrito`),
  UNIQUE KEY `unique_producto_usuario` (`id_usuario`,`id_producto`),
  KEY `id_producto` (`id_producto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `categorias`
--

CREATE TABLE IF NOT EXISTS `categorias` (
  `id_categoria` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `estado` enum('activo','inactivo') DEFAULT 'activo',
  PRIMARY KEY (`id_categoria`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `categorias`
--

INSERT IGNORE INTO `categorias` (`id_categoria`, `nombre`, `descripcion`, `estado`) VALUES
(1, 'Smartphones', 'Teléfonos móviles de última generación', 'activo'),
(2, 'Laptops', 'Computadoras portátiles para trabajo y gaming', 'activo'),
(3, 'Tablets', 'Dispositivos táctiles para productividad y entretenimiento', 'activo'),
(4, 'Accesorios', 'Complementos y accesorios para dispositivos electrónicos', 'activo');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `detalles_pedido`
--

CREATE TABLE IF NOT EXISTS `detalles_pedido` (
  `id_detalle` int(11) NOT NULL AUTO_INCREMENT,
  `id_pedido` int(11) NOT NULL,
  `id_producto` int(11) NOT NULL,
  `cantidad` int(11) NOT NULL,
  `precio_unitario` decimal(10,2) NOT NULL,
  `subtotal` decimal(10,2) NOT NULL,
  PRIMARY KEY (`id_detalle`),
  KEY `id_pedido` (`id_pedido`),
  KEY `id_producto` (`id_producto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `pedidos`
--

CREATE TABLE IF NOT EXISTS `pedidos` (
  `id_pedido` int(11) NOT NULL AUTO_INCREMENT,
  `id_usuario` int(11) NOT NULL,
  `fecha_pedido` timestamp NOT NULL DEFAULT current_timestamp(),
  `fecha_actualizacion` timestamp NULL DEFAULT NULL,
  `total` decimal(10,2) NOT NULL,
  `estado` enum('pendiente','en_proceso','enviado','entregado','cancelado') DEFAULT 'pendiente',
  `direccion_envio` text NOT NULL,
  `telefono` varchar(20) NOT NULL,
  `metodo_pago` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id_pedido`),
  KEY `id_usuario` (`id_usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `productos`
--

CREATE TABLE IF NOT EXISTS `productos` (
  `id_producto` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `precio` decimal(10,2) NOT NULL,
  `stock` int(11) NOT NULL DEFAULT 0,
  `id_categoria` int(11) DEFAULT NULL,
  `imagen` varchar(255) DEFAULT NULL,
  `estado` enum('activo','inactivo') DEFAULT 'activo',
  PRIMARY KEY (`id_producto`),
  KEY `id_categoria` (`id_categoria`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `productos`
--

INSERT IGNORE INTO `productos` (`id_producto`, `nombre`, `descripcion`, `precio`, `stock`, `id_categoria`, `imagen`, `estado`) VALUES
(1, 'iPhone 15 Pro', 'El último iPhone con chip A17 Pro y cámara de 48MP.', 999.99, 50, 1, 'iphone15pro.jpg', 'activo'),
(2, 'Samsung Galaxy S24 Ultra', 'Potencia y versatilidad con S Pen incluido.', 1199.99, 40, 1, 's24ultra.jpg', 'activo'),
(3, 'Google Pixel 8 Pro', 'La mejor cámara en un smartphone Android.', 899.99, 35, 1, 'pixel8pro.jpg', 'activo'),
(4, 'Xiaomi 14 Pro', 'Rendimiento premium a un precio competitivo.', 799.99, 45, 1, 'xiaomi14pro.jpg', 'activo'),
(5, 'OnePlus 12', 'Carga rápida y rendimiento excepcional.', 699.99, 30, 1, 'oneplus12.jpg', 'activo'),
(6, 'MacBook Pro M3', 'Potencia profesional con chip M3 y pantalla Liquid Retina XDR.', 1999.99, 25, 2, 'macbookprom3.jpg', 'activo'),
(7, 'Dell XPS 15', 'Diseño premium con pantalla OLED y procesador Intel Core i9.', 1799.99, 20, 2, 'dellxps15.jpg', 'activo'),
(8, 'Lenovo ThinkPad X1', 'Laptop empresarial con seguridad avanzada y gran duración de batería.', 1599.99, 30, 2, 'thinkpadx1.jpg', 'activo'),
(9, 'ASUS ROG Zephyrus', 'Laptop gaming con RTX 4090 y pantalla de 240Hz.', 2499.99, 15, 2, 'rogzephyrus.jpg', 'activo'),
(10, 'HP Spectre x360', 'Convertible premium con pantalla táctil y diseño elegante.', 1299.99, 25, 2, 'spectrex360.jpg', 'activo'),
(11, 'iPad Pro M2', 'Potencia profesional en formato tablet con pantalla Liquid Retina.', 899.99, 40, 3, 'ipadpro.jpg', 'activo'),
(12, 'Samsung Galaxy Tab S9 Ultra', 'Tablet Android premium con S Pen y pantalla AMOLED.', 799.99, 35, 3, 'tabs9ultra.jpg', 'activo'),
(13, 'Microsoft Surface Pro 9', 'Tablet convertible con Windows 11 y teclado desmontable.', 999.99, 30, 3, 'surfacepro9.jpg', 'activo'),
(14, 'Lenovo Tab P12 Pro', 'Tablet Android con pantalla OLED y altavoces JBL.', 599.99, 25, 3, 'tabp12pro.jpg', 'activo'),
(15, 'Xiaomi Pad 6 Pro', 'Tablet de gama alta con carga rápida y gran batería.', 499.99, 40, 3, 'pad6pro.jpg', 'activo'),
(16, 'AirPods Pro 2', 'Auriculares inalámbricos con cancelación activa de ruido.', 249.99, 100, 4, 'airpodspro2.jpg', 'activo'),
(17, 'Samsung Galaxy Watch 6', 'Smartwatch con monitor de salud avanzado y diseño elegante.', 299.99, 50, 4, 'galaxywatch6.jpg', 'activo'),
(18, 'Logitech MX Master 3S', 'Ratón premium para productividad con scroll electromagnético.', 99.99, 75, 4, 'mxmaster3s.jpg', 'activo'),
(19, 'Samsung 49\" Odyssey G9', 'Monitor gaming curvo con resolución 5120x1440 y 240Hz.', 999.99, 20, 4, 'odysseyg9.jpg', 'activo'),
(20, 'Apple Magic Keyboard', 'Teclado inalámbrico con diseño minimalista y gran duración de batería.', 149.99, 60, 4, 'magickeyboard.jpg', 'activo');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `usuarios`
--

CREATE TABLE IF NOT EXISTS `usuarios` (
  `id_usuario` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `tipo_usuario` enum('admin','usuario') NOT NULL DEFAULT 'usuario',
  `direccion` text DEFAULT NULL,
  `telefono` varchar(20) DEFAULT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_usuario`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `usuarios`
--

INSERT IGNORE INTO `usuarios` (`id_usuario`, `nombre`, `email`, `password`, `tipo_usuario`, `direccion`, `telefono`, `fecha_registro`) VALUES
(2, 'Jhonathan', 'jhonn@gmail.com', 'pbkdf2:sha256:600000$rHe1G8eohPxKcHlz$92e7bce188a79194f9936b8f695711d5c19d04e0b0cec1395660a043f8efacbe', 'admin', 'Aniceto Arce 46', '75781303', '2025-06-13 07:30:21'),
(3, 'admin', 'admin1@gmail.com', 'admin123', 'admin', 'pampas', '75781303', '2025-06-13 03:32:48'),
(4, 'juanjo', 'juanjo@gmail.com', 'pbkdf2:sha256:600000$d9D8sNtJojwcVmDP$a1c6d816e773310c9ff47acfe6b2655253ef2171f6f5c876f09d2d31f275e3d4', 'usuario', 'lomaspampas', '456767678', '2025-06-13 07:38:29');

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `carrito`
--
ALTER TABLE `carrito`
  ADD CONSTRAINT `carrito_ibfk_1` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuario`) ON DELETE CASCADE,
  ADD CONSTRAINT `carrito_ibfk_2` FOREIGN KEY (`id_producto`) REFERENCES `productos` (`id_producto`) ON DELETE CASCADE;

--
-- Filtros para la tabla `detalles_pedido`
--
ALTER TABLE `detalles_pedido`
  ADD CONSTRAINT `detalles_pedido_ibfk_1` FOREIGN KEY (`id_pedido`) REFERENCES `pedidos` (`id_pedido`) ON DELETE CASCADE,
  ADD CONSTRAINT `detalles_pedido_ibfk_2` FOREIGN KEY (`id_producto`) REFERENCES `productos` (`id_producto`) ON DELETE CASCADE;

--
-- Filtros para la tabla `pedidos`
--
ALTER TABLE `pedidos`
  ADD CONSTRAINT `pedidos_ibfk_1` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuario`) ON DELETE CASCADE;

--
-- Filtros para la tabla `productos`
--
ALTER TABLE `productos`
  ADD CONSTRAINT `productos_ibfk_1` FOREIGN KEY (`id_categoria`) REFERENCES `categorias` (`id_categoria`) ON DELETE SET NULL;

COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;

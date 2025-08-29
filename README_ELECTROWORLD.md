# ElectroWorld - Sistema de Ventas y Servicios de Mantenimiento

## Cambios Realizados

### 1. Cambio de Marca: TechStore → ElectroWorld
- **Nombre de la empresa**: Cambiado de "TechStore" a "ElectroWorld"
- **Email de contacto**: Actualizado a `electro.world@gmail.com`
- **Email de servicios**: `servicios@electro.world`
- **Títulos de página**: Actualizados para reflejar la nueva marca

### 2. Actualización de Estilos CSS
- **Colores principales**: Cambiados de azul a verde llamativo
- **Paleta de colores**:
  - Verde primario: `#28a745`
  - Verde secundario: `#20c997`
  - Verde oscuro: `#146c43`
  - Verde claro: `#d1e7dd`
- **Archivo CSS**: `static/css/styles.css` con estilos personalizados
- **Efectos visuales**: Hover effects, transiciones y sombras en verde

### 3. Nuevo Apartado de Servicios de Mantenimiento
- **Página dedicada**: `templates/servicios_mantenimiento.html`
- **Servicios principales**:
  - Mantenimiento de Laptops (Bs. 150)
  - Reparación de Smartphones (Bs. 200)
  - Reparación de PC (Bs. 100)
  - Seguridad Informática (Bs. 80)
  - Configuración de Redes (Bs. 120)
  - Recuperación de Datos (Bs. 250)

### 4. Actualización de Base de Datos
- **Archivo SQL**: `actualizacion_electroworld.sql`
- **Nueva categoría**: "Servicios de Mantenimiento"
- **Nuevas tablas**:
  - `servicios_mantenimiento`: Catálogo de servicios
  - `solicitudes_servicio`: Solicitudes de clientes
  - `historial_servicios`: Registro de trabajos realizados
- **Productos de servicio**: 8 nuevos productos de mantenimiento

### 5. Navegación Actualizada
- **Nuevo enlace**: "Servicios de Mantenimiento" en la barra de navegación
- **Iconos**: Uso de Bootstrap Icons para mejor UX
- **Responsive**: Diseño adaptativo para dispositivos móviles

## Estructura de Archivos Modificados

```
ProyectoFinal/
├── static/
│   └── css/
│       └── styles.css (NUEVO - Estilos personalizados en verde)
├── templates/
│   ├── base.html (ACTUALIZADO - Nombre y navegación)
│   ├── index.html (ACTUALIZADO - Sección de servicios)
│   └── servicios_mantenimiento.html (NUEVO - Página de servicios)
├── app.py (ACTUALIZADO - Nueva ruta para servicios)
├── actualizacion_electroworld.sql (NUEVO - Script de BD)
└── README_ELECTROWORLD.md (NUEVO - Este archivo)
```

## Instalación y Configuración

### 1. Aplicar Cambios de Base de Datos
```sql
-- Ejecutar el archivo de actualización
mysql -u root -p < actualizacion_electroworld.sql
```

### 2. Verificar Archivos CSS
- Asegurarse de que `static/css/styles.css` esté en su lugar
- Verificar que las plantillas incluyan el CSS personalizado

### 3. Reiniciar la Aplicación
```bash
python app.py
```

## Características de los Servicios de Mantenimiento

### Servicios Disponibles
1. **Mantenimiento de Laptops**
   - Limpieza interna y externa
   - Cambio de pasta térmica
   - Optimización del sistema
   - Diagnóstico completo

2. **Reparación de Smartphones**
   - Cambio de pantalla
   - Reemplazo de batería
   - Reparación de software
   - Recuperación de datos

3. **Reparación de PC**
   - Ensamblaje completo
   - Actualización de componentes
   - Instalación de software
   - Diagnóstico de problemas

4. **Seguridad Informática**
   - Instalación de antivirus
   - Limpieza de malware
   - Configuración de firewall
   - Backup de seguridad

5. **Redes y Conectividad**
   - Configuración de WiFi
   - Reparación de conexiones
   - Optimización de red
   - Instalación de routers

### Proceso de Trabajo
1. **Diagnóstico**: Evaluación del problema y presupuesto
2. **Reparación**: Trabajo técnico profesional
3. **Pruebas**: Verificación de funcionamiento
4. **Garantía**: Entrega con garantía y soporte

## Información de Contacto

- **Teléfono**: +591 75781303
- **WhatsApp**: +591 75781303
- **Email General**: electro.world@gmail.com
- **Email Servicios**: servicios@electro.world
- **Dirección**: Calle Apruebenos Ingeniero #100

## Tecnologías Utilizadas

- **Backend**: Python Flask
- **Base de Datos**: MySQL
- **Frontend**: HTML5, CSS3, Bootstrap 5
- **Iconos**: Bootstrap Icons
- **Estilos**: CSS personalizado con variables CSS

## Notas de Desarrollo

- Los estilos están optimizados para usuarios mayores (interfaces simplificadas)
- Colores verdes llamativos para mejor visibilidad
- Diseño responsive para todos los dispositivos
- Integración completa con el sistema existente de ventas

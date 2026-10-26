-- Esquema v1: Datos generales del proyecto + auditoría.
-- Los módulos de almacén (ítems, movimientos, kardex) se agregarán en migraciones v2+.

CREATE TABLE IF NOT EXISTS proyecto (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    activo                 INTEGER NOT NULL DEFAULT 0 CHECK (activo IN (0, 1)),
    estado                 TEXT    NOT NULL DEFAULT 'EN_EJECUCION'
                           CHECK (estado IN ('EN_EJECUCION','PARALIZADA','CULMINADA','LIQUIDADA')),

    -- Empresa / entidad
    tipo_entidad           TEXT    NOT NULL DEFAULT 'ENTIDAD_PUBLICA'
                           CHECK (tipo_entidad IN ('ENTIDAD_PUBLICA','EMPRESA_PRIVADA','CONSORCIO')),
    razon_social           TEXT    NOT NULL CHECK (trim(razon_social) <> ''),
    ruc                    TEXT    NOT NULL CHECK (length(ruc) = 11),
    direccion              TEXT,
    telefono               TEXT,
    correo                 TEXT,
    logo_path              TEXT,

    -- Obra
    nombre_obra            TEXT    NOT NULL CHECK (trim(nombre_obra) <> ''),
    nombre_corto           TEXT,
    cui                    TEXT,
    modalidad              TEXT    NOT NULL DEFAULT 'ADMINISTRACION_DIRECTA'
                           CHECK (modalidad IN ('ADMINISTRACION_DIRECTA','CONTRATA')),
    contratista            TEXT,
    contratista_ruc        TEXT,
    numero_contrato        TEXT,
    fuente_financiamiento  TEXT,
    presupuesto            REAL    CHECK (presupuesto IS NULL OR presupuesto >= 0),

    -- Ubicación
    departamento           TEXT,
    provincia              TEXT,
    distrito               TEXT,
    localidad              TEXT,

    -- Fechas (ISO yyyy-mm-dd)
    fecha_entrega_terreno  TEXT,
    fecha_inicio           TEXT,
    plazo_dias             INTEGER CHECK (plazo_dias IS NULL OR plazo_dias > 0),
    fecha_termino_prog     TEXT,
    fecha_termino_real     TEXT,

    -- Configuración de reportes
    moneda_codigo          TEXT    NOT NULL DEFAULT 'PEN',
    moneda_simbolo         TEXT    NOT NULL DEFAULT 'S/',
    denominacion_anio      TEXT,
    encabezado_extra       TEXT,
    pie_reporte            TEXT,
    mostrar_logo           INTEGER NOT NULL DEFAULT 1,
    firma_residente        INTEGER NOT NULL DEFAULT 1,
    firma_supervisor       INTEGER NOT NULL DEFAULT 1,
    firma_almacenero       INTEGER NOT NULL DEFAULT 1,

    creado_en              TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    actualizado_en         TEXT    NOT NULL DEFAULT (datetime('now','localtime')),

    CHECK (fecha_inicio IS NULL OR fecha_termino_prog IS NULL OR fecha_termino_prog >= fecha_inicio),
    CHECK (fecha_inicio IS NULL OR fecha_termino_real IS NULL OR fecha_termino_real >= fecha_inicio)
);

-- Solo un proyecto activo a la vez.
CREATE UNIQUE INDEX IF NOT EXISTS ux_proyecto_activo ON proyecto (activo) WHERE activo = 1;
-- El CUI no se repite entre proyectos.
CREATE UNIQUE INDEX IF NOT EXISTS ux_proyecto_cui ON proyecto (cui) WHERE cui IS NOT NULL AND cui <> '';

CREATE TABLE IF NOT EXISTS proyecto_responsable (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    proyecto_id  INTEGER NOT NULL REFERENCES proyecto (id) ON DELETE CASCADE,
    rol          TEXT    NOT NULL CHECK (rol IN ('RESIDENTE','SUPERVISOR','ALMACENERO','ADMINISTRADOR')),
    nombre       TEXT    NOT NULL CHECK (trim(nombre) <> ''),
    profesion    TEXT,
    colegiatura  TEXT,
    dni          TEXT,
    telefono     TEXT,
    correo       TEXT,
    UNIQUE (proyecto_id, rol)
);

CREATE TABLE IF NOT EXISTS auditoria (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha       TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    usuario     TEXT    NOT NULL,
    modulo      TEXT    NOT NULL,
    accion      TEXT    NOT NULL,
    entidad     TEXT    NOT NULL,
    entidad_id  INTEGER,
    detalle     TEXT
);
CREATE INDEX IF NOT EXISTS ix_auditoria_entidad ON auditoria (entidad, entidad_id);

# Monitor de Convocatorias de Plazas Universitarias

Sistema automático, gratuito y sin mantenimiento que revisa cada día (a
las 08:00 y a las 20:00, hora de Madrid) si hay convocatorias nuevas de
plazas de profesorado en varias universidades españolas relacionadas
con tu perfil, y te avisa por correo electrónico. Se ejecuta entero en
**GitHub Actions**: no necesitas tener el ordenador encendido.

## ⚠️ Importante: lee esto antes de empezar

- Los scrapers de la **Universidad de Valladolid (UVa)** y la **UNED**
  se han verificado contra la estructura real de sus páginas.
- Los scrapers de **UNIR, UOC, Universidad Isabel I y VIU** usan una
  lógica genérica (buscan enlaces con palabras como "profesor",
  "plaza", "vacante"...) porque sus páginas de empleo cambian con
  frecuencia y algunas cargan las ofertas mediante JavaScript, que este
  sistema (deliberadamente simple, sin navegador) no puede ejecutar.
  **Después de la primera ejecución, revisa el log** (ver más abajo)
  para comprobar si esas cuatro universidades están devolviendo
  resultados razonables, y ajusta el archivo correspondiente en
  `universidades/` si hace falta. El apartado
  ["Cómo añadir o ajustar una universidad"](#cómo-añadir-o-ajustar-una-universidad)
  explica cómo hacerlo.
- Nada de esto requiere pagar nada: GitHub Actions es gratuito para
  repositorios públicos (y da 2.000 minutos/mes gratis en repositorios
  privados, más que suficiente para dos ejecuciones diarias de un
  script tan ligero).

## Índice

1. [Cómo crear el repositorio](#1-cómo-crear-el-repositorio)
2. [Cómo configurar el correo electrónico](#2-cómo-configurar-el-correo-electrónico)
3. [Cómo configurar GitHub Actions](#3-cómo-configurar-github-actions)
4. [Cómo probar el sistema localmente](#4-cómo-probar-el-sistema-localmente)
5. [Cómo modificar las palabras clave](#5-cómo-modificar-las-palabras-clave)
6. [Cómo añadir o ajustar una universidad](#6-cómo-añadir-o-ajustar-una-universidad)
7. [Cómo funciona por dentro](#7-cómo-funciona-por-dentro)
8. [Solución de problemas](#8-solución-de-problemas)

---

## 1. Cómo crear el repositorio

1. Entra en [github.com](https://github.com) e inicia sesión (o crea una
   cuenta gratuita).
2. Pulsa el botón **"New"** (o el "+" de arriba a la derecha → "New
   repository").
3. Ponle un nombre, por ejemplo `monitor-convocatorias`.
4. Puedes dejarlo como repositorio **público** (así GitHub Actions es
   100% gratis sin límites prácticos) o **privado** si prefieres
   privacidad; con privado también funciona, solo consume minutos de tu
   cuota gratuita mensual (muy poco para este uso).
5. Pulsa **"Create repository"**.
6. Sube todos los archivos de esta carpeta (`convocatorias/`) al
   repositorio. Las dos formas más sencillas:
   - **Desde el navegador**: en la página del repositorio recién creado,
     pulsa "uploading an existing file" y arrastra todos los archivos y
     carpetas.
   - **Desde tu ordenador con git instalado**:
     ```bash
     cd convocatorias
     git init
     git add .
     git commit -m "Primera versión del monitor de convocatorias"
     git branch -M main
     git remote add origin https://github.com/TU-USUARIO/monitor-convocatorias.git
     git push -u origin main
     ```

## 2. Cómo configurar el correo electrónico

El sistema envía los avisos usando **SMTP normal y corriente**, así que
te sirve cualquier cuenta de correo. El ejemplo más sencillo es Gmail:

1. Ve a tu [Cuenta de Google → Seguridad](https://myaccount.google.com/security).
2. Activa la **verificación en dos pasos** si no la tienes activada ya
   (es obligatoria para el siguiente paso).
3. Busca **"Contraseñas de aplicaciones"** (searcha "contraseñas de
   aplicaciones" en el buscador de la propia página de Google) y genera
   una nueva, por ejemplo con el nombre "monitor-convocatorias". Google
   te dará una contraseña de 16 caracteres: **cópiala**, es la única vez
   que se muestra.
4. Los datos SMTP de Gmail son:
   - Host: `smtp.gmail.com`
   - Puerto: `587`
   - Usuario: tu dirección de Gmail completa
   - Contraseña: la contraseña de aplicación de 16 caracteres (NO tu
     contraseña normal de Gmail)

Si usas Outlook/Hotmail, Yahoo u otro proveedor, el proceso es
equivalente: busca "contraseña de aplicación" + el nombre de tu
proveedor, y sus datos de servidor SMTP (para Outlook: `smtp.office365.com`,
puerto `587`).

## 3. Cómo configurar GitHub Actions

Los datos de correo **nunca se escriben en el código** (para que nadie
más pueda verlos si el repositorio es público). Se guardan como
"secretos" cifrados de GitHub:

1. En tu repositorio, ve a **Settings → Secrets and variables → Actions**.
2. Pulsa **"New repository secret"** y crea, uno por uno, estos cinco
   secretos:

   | Nombre del secreto | Valor |
   |---|---|
   | `SMTP_HOST` | `smtp.gmail.com` (o el de tu proveedor) |
   | `SMTP_PORT` | `587` |
   | `SMTP_USER` | tu dirección de correo remitente |
   | `SMTP_PASSWORD` | la contraseña de aplicación de 16 caracteres |
   | `EMAIL_DESTINO` | el correo donde quieres recibir los avisos (puede ser el mismo que `SMTP_USER`) |

3. Ve a la pestaña **"Actions"** de tu repositorio. Si aparece un aviso
   pidiendo habilitar los workflows, actívalo.
4. El workflow ya está programado (ver `.github/workflows/monitor.yml`)
   para ejecutarse automáticamente a las 08:00 y a las 20:00, hora de
   Madrid, todos los días. No necesitas hacer nada más.
5. Para lanzar una primera ejecución de prueba sin esperar al horario
   programado: pestaña **Actions → Monitor de convocatorias → Run
   workflow → Run workflow**.

## 4. Cómo probar el sistema localmente

Necesitas Python 3.10 o superior instalado.

```bash
cd convocatorias
pip install -r requirements.txt

# Modo prueba: descarga y filtra convocatorias, las muestra en el log,
# pero NO envía ningún correo ni las marca como notificadas.
python main.py --prueba

# Probar solo una universidad (por ejemplo, la UVa):
python main.py --prueba --solo uva

# Ejecución real (necesita las variables de entorno de correo definidas
# en tu terminal, no en GitHub):
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=tu_correo@gmail.com
export SMTP_PASSWORD=tu_contraseña_de_aplicacion
export EMAIL_DESTINO=tu_correo@gmail.com
python main.py
```

El log de cada ejecución se guarda en `logs/monitor.log`.

## 5. Cómo modificar las palabras clave

Abre `config/keywords.yaml`. Cada línea que empieza por `- "..."` es una
palabra o frase clave. Para añadir una nueva, añade una línea igual con
tu término; para quitar una, borra su línea. No hace falta tocar ningún
archivo `.py` ni volver a desplegar nada: el cambio se aplica en la
siguiente ejecución programada (o al hacer `git push`, el propio
workflow lo recogerá).

## 6. Cómo añadir o ajustar una universidad

### Añadir una universidad nueva

1. Crea un archivo nuevo en `universidades/`, por ejemplo
   `universidades/miuniversidad.py`, con una clase que herede de
   `ScraperUniversidad` (ver `universidades/base.py`) o, si es una
   universidad online sencilla, de `ScraperGenerico`
   (`universidades/generico.py`).
2. Añade una entrada nueva en la lista `universidades:` de
   `config/config.yaml`, con el `id`, `nombre`, `modulo` (nombre del
   archivo sin `.py`), `clase` y `url` correspondientes.
3. Listo. `main.py` la detectará automáticamente en la siguiente
   ejecución.

### Eliminar o desactivar una universidad

En `config/config.yaml`, pon `activa: false` en su entrada (para poder
reactivarla fácilmente más adelante) o borra directamente su bloque.

### Ajustar un scraper que no encuentra resultados

Si tras la primera ejecución una universidad (típicamente UNIR, UOC,
Isabel I o VIU) aparece en el log con "0 posibles vacantes encontradas":

1. Abre la URL de esa universidad en tu navegador y comprueba, con las
   herramientas de desarrollador (F12 → pestaña "Red"/"Network"), si
   las ofertas de empleo se cargan mediante una llamada a una API que
   devuelve JSON. Si es así, es la vía más fiable: se puede pedir esa
   misma URL con `requests` directamente en el scraper, sin necesidad
   de "renderizar" la página.
2. Si la página es HTML estático pero el scraper genérico no encuentra
   nada relevante, añade una versión específica de
   `obtener_convocatorias` en el archivo de esa universidad (siguiendo
   el ejemplo de `universidades/uva.py` o `universidades/uned.py` como
   guía) en lugar de heredar de `ScraperGenerico`.

## 7. Cómo funciona por dentro

```
convocatorias/
├── main.py                  # Orquesta todo el proceso
├── config/
│   ├── config.yaml          # Universidades activas, comportamiento, correo
│   └── keywords.yaml        # Palabras clave que activan un aviso
├── universidades/
│   ├── base.py               # Clase abstracta + modelo "Convocatoria"
│   ├── generico.py           # Scraper heurístico reutilizable
│   ├── uva.py, uned.py, ...  # Un archivo por universidad
├── database/
│   └── db.py                 # SQLite: evita avisos duplicados
├── utils/
│   ├── email_sender.py       # Envío SMTP
│   ├── date_utils.py         # Parseo de fechas y cálculo de plazos
│   └── logger.py             # Logging a consola + archivo
└── .github/workflows/
    └── monitor.yml            # Programación en GitHub Actions
```

En cada ejecución, `main.py`:

1. Lee `config.yaml` y `keywords.yaml`.
2. Para cada universidad activa, instancia su scraper y descarga sus
   convocatorias (con 2 reintentos automáticos si falla la conexión).
3. Filtra por palabras clave (en título o área).
4. Descarta las convocatorias ya cerradas o ya notificadas antes
   (comprobando `database/convocatorias.db`).
5. Envía un correo por cada convocatoria nueva y la registra en la
   base de datos para no repetirla nunca.
6. Si una universidad falla, el error queda registrado en el log y el
   sistema continúa con el resto sin interrumpirse.

La base de datos SQLite se guarda directamente en el repositorio: el
propio workflow de GitHub Actions la actualiza y la "commitea" tras
cada ejecución, así que persiste entre ejecuciones sin necesidad de
ningún servicio externo de pago.

## 8. Solución de problemas

- **No me llega ningún correo aunque el log dice "nuevas: 1"**: revisa
  que los 5 secretos estén bien escritos en GitHub (Settings → Secrets
  and variables → Actions) y que la contraseña sea la "de aplicación"
  de 16 caracteres, no tu contraseña normal. Revisa también la carpeta
  de spam.
- **El workflow no se ha ejecutado nunca solo**: comprueba en la
  pestaña "Actions" que los workflows están habilitados, y que no han
  pasado más de 60 días sin actividad en el repositorio (GitHub
  desactiva automáticamente los cron de repositorios inactivos; basta
  con volver a habilitarlo manualmente desde esa misma pestaña).
- **Una universidad da error de conexión constantemente**: revisa que
  la URL en `config.yaml` sigue siendo válida (las universidades
  rediseñan sus webs de vez en cuando); actualízala si ha cambiado.
- **Quiero recibir los avisos también aunque la convocatoria no tenga
  fecha límite clara**: así es como funciona ya por defecto; solo se
  descartan las convocatorias en las que SÍ se detectó una fecha límite
  y esta ya pasó.

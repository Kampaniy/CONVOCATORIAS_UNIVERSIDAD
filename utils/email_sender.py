"""Envío de notificaciones por correo electrónico mediante SMTP estándar.

Deliberadamente no depende de ningún servicio de terceros (SendGrid,
Mailgun, etc.) para que el sistema siga siendo gratuito: basta con una
cuenta de correo normal (Gmail, Outlook...) y una "contraseña de
aplicación".
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger("monitor_convocatorias")


@dataclass
class CredencialesSMTP:
    """Agrupa los datos de conexión SMTP necesarios para enviar correo."""

    host: str
    puerto: int
    usuario: str
    contrasena: str
    destino: str
    usar_tls: bool = True


class ErrorEnvioCorreo(Exception):
    """Se lanza cuando el envío de un correo falla tras los reintentos."""


def construir_cuerpo_html(
    universidad: str,
    titulo: str,
    area: Optional[str],
    fecha_publicacion: Optional[str],
    fecha_limite: Optional[str],
    dias_restantes: Optional[int],
    enlace: str,
) -> str:
    """Construye el cuerpo HTML del correo de aviso de una convocatoria.

    Todos los campos opcionales se muestran como "No disponible" si no
    se pudieron extraer de la página de origen.
    """
    area_txt = area or "No disponible"
    fecha_pub_txt = fecha_publicacion or "No disponible"
    fecha_lim_txt = fecha_limite or "No disponible"
    dias_txt = f"{dias_restantes} días" if dias_restantes is not None else "No disponible"

    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #222;">
        <h2 style="color:#0b3d91;">Nueva convocatoria detectada</h2>
        <table cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
          <tr><td style="font-weight:bold;">Universidad:</td><td>{universidad}</td></tr>
          <tr><td style="font-weight:bold;">Título:</td><td>{titulo}</td></tr>
          <tr><td style="font-weight:bold;">Área:</td><td>{area_txt}</td></tr>
          <tr><td style="font-weight:bold;">Fecha de publicación:</td><td>{fecha_pub_txt}</td></tr>
          <tr><td style="font-weight:bold;">Fecha límite de solicitud:</td><td>{fecha_lim_txt}</td></tr>
          <tr><td style="font-weight:bold;">Días restantes:</td><td>{dias_txt}</td></tr>
          <tr><td style="font-weight:bold;">Enlace:</td><td><a href="{enlace}">{enlace}</a></td></tr>
        </table>
      </body>
    </html>
    """


def enviar_correo(
    credenciales: CredencialesSMTP,
    asunto: str,
    cuerpo_html: str,
    intentos: int = 2,
) -> None:
    """Envía un correo electrónico HTML mediante SMTP con reintentos simples.

    Args:
        credenciales: Datos de conexión y destino del correo.
        asunto: Asunto del correo.
        cuerpo_html: Cuerpo del correo en formato HTML.
        intentos: Número máximo de intentos antes de lanzar una excepción.

    Raises:
        ErrorEnvioCorreo: Si todos los intentos de envío fallan.
    """
    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = asunto
    mensaje["From"] = credenciales.usuario
    mensaje["To"] = credenciales.destino
    mensaje.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    ultimo_error: Optional[Exception] = None
    for intento in range(1, intentos + 1):
        try:
            with smtplib.SMTP(credenciales.host, credenciales.puerto, timeout=20) as servidor:
                if credenciales.usar_tls:
                    servidor.starttls()
                servidor.login(credenciales.usuario, credenciales.contrasena)
                servidor.sendmail(
                    credenciales.usuario, [credenciales.destino], mensaje.as_string()
                )
            logger.info("Correo enviado correctamente a %s", credenciales.destino)
            return
        except Exception as error:  # noqa: BLE001 - queremos capturar cualquier fallo SMTP
            ultimo_error = error
            logger.warning("Intento %d/%d de envío de correo fallido: %s", intento, intentos, error)

    raise ErrorEnvioCorreo(f"No se pudo enviar el correo tras {intentos} intentos: {ultimo_error}")

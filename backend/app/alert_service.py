from flask import current_app


class AlertService:
    """Service for handling system-wide alerts and critical notifications"""

    @staticmethod
    def send_alert(message, level="ERROR", context=None):
        """
        Send an alert through configured channels.
        In this phase, it logs to a special 'alerts' logger.
        """
        severity = level.upper()
        alert_msg = f"[SYSTEM ALERT] [{severity}] {message}"
        if context:
            alert_msg += f" | Context: {context}"

        # Log to system logger
        if severity == "CRITICAL":
            current_app.logger.critical(alert_msg)
        else:
            current_app.logger.error(alert_msg)

        # Development placeholder for Email/SMS/Webhook integration
        if not current_app.debug:
            # Here you would integrate with SendGrid, Twilio, Slack, etc.
            # Example: SlackService.send_message(alert_msg)
            pass

    @staticmethod
    def log_critical_error(error, endpoint=None):
        """Log and alert on a critical system failure"""
        message = f"Critical error encountered: {str(error)}"
        context = {"endpoint": endpoint} if endpoint else None
        AlertService.send_alert(message, level="CRITICAL", context=context)

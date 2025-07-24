"""
Alert Management System for Indexing QA
Handles Slack notifications, email alerts, and alert throttling
"""

import json
import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
import logging

from ..models.models import AlertRecord, ChunkRecord, QualityCheckRecord, FlagStatus
from ..core.config import get_settings
from ..database.database import get_db_context


class AlertType(str, Enum):
    """Types of alerts that can be sent"""
    RULES_ENGINE_FAILURE = "rules_engine_failure"
    LLM_VALIDATION_FAILURE = "llm_validation_failure"
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    COST_THRESHOLD_EXCEEDED = "cost_threshold_exceeded"
    QUALITY_THRESHOLD_EXCEEDED = "quality_threshold_exceeded"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertManager:
    """Manages alert sending and throttling"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        
        # Alert history for throttling
        self.alert_history: Dict[str, datetime] = {}
        
        # Email recipients file
        self.alert_emails_file = os.path.join(os.path.dirname(__file__), 'alert_emails.json')
        self._ensure_alert_emails_file()
        
        # Alert template file
        self.alert_template_file = os.path.join(os.path.dirname(__file__), 'alert_template.json')
        self._ensure_alert_template_file()
    
    def _ensure_alert_emails_file(self):
        """Ensure the alert emails file exists with default configuration"""
        if not os.path.exists(self.alert_emails_file):
            default_config = {
                "to": ["skand.vijay@capacity.com"],
                "cc": []
            }
            try:
                with open(self.alert_emails_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                self.logger.info(f"Created default alert emails file: {self.alert_emails_file}")
            except Exception as e:
                self.logger.error(f"Failed to create alert emails file: {e}")
    
    def _ensure_alert_template_file(self):
        """Ensure the alert template file exists with default configuration"""
        if not os.path.exists(self.alert_template_file):
            default_template = {
                "subject": "[{severity}] Indexing QA Alert: {alert_type}",
                "body": """🚨 Indexing QA Alert

Type: {alert_type}
Severity: {severity}
Time: {timestamp}

Message: {message}

Record ID: {record_id}
Trace ID: {trace_id}

Details:
{details}

---
This is an automated alert from the Indexing QA system.
Configure alerts at: http://localhost:3000/settings
"""
            }
            try:
                with open(self.alert_template_file, 'w') as f:
                    json.dump(default_template, f, indent=2)
                self.logger.info(f"Created default alert template file: {self.alert_template_file}")
            except Exception as e:
                self.logger.error(f"Failed to create alert template file: {e}")
    
    def load_email_recipients(self) -> tuple[List[str], List[str]]:
        """Load email recipients (To/CC) from file"""
        try:
            if os.path.exists(self.alert_emails_file):
                with open(self.alert_emails_file, 'r') as f:
                    data = json.load(f)
                    return data.get('to', []), data.get('cc', [])
        except Exception as e:
            self.logger.error(f"Failed to load alert emails: {e}")
        
        # Fallback to settings
        return self.settings.email_recipients, []
    
    def save_email_recipients(self, to_list: List[str], cc_list: List[str]):
        """Save email recipients to file"""
        try:
            config = {
                "to": to_list,
                "cc": cc_list
            }
            with open(self.alert_emails_file, 'w') as f:
                json.dump(config, f, indent=2)
            self.logger.info("Updated alert email recipients")
        except Exception as e:
            self.logger.error(f"Failed to save alert emails: {e}")
    
    def load_alert_template(self) -> Dict[str, str]:
        """Load alert template from file"""
        try:
            if os.path.exists(self.alert_template_file):
                with open(self.alert_template_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load alert template: {e}")
        
        # Return default template
        return {
            "subject": "[{severity}] Indexing QA Alert: {alert_type}",
            "body": """🚨 Indexing QA Alert

Type: {alert_type}
Severity: {severity}
Time: {timestamp}

Message: {message}

Record ID: {record_id}
Trace ID: {trace_id}

Details:
{details}

---
This is an automated alert from the Indexing QA system.
Configure alerts at: http://localhost:3000/settings
"""
        }
    
    def save_alert_template(self, template: Dict[str, str]):
        """Save alert template to file"""
        try:
            with open(self.alert_template_file, 'w') as f:
                json.dump(template, f, indent=2)
            self.logger.info("Updated alert template")
        except Exception as e:
            self.logger.error(f"Failed to save alert template: {e}")
    
    def get_email_recipients(self) -> tuple[List[str], List[str]]:
        """Get current email recipients"""
        return self.load_email_recipients()
    
    def get_alert_template(self) -> Dict[str, str]:
        """Get current alert template"""
        return self.load_alert_template()
    
    def add_email_recipient(self, email: str, typ: str = 'to'):
        """Add an email recipient"""
        to_list, cc_list = self.load_email_recipients()
        
        if typ == 'to':
            if email not in to_list:
                to_list.append(email)
        elif typ == 'cc':
            if email not in cc_list:
                cc_list.append(email)
        
        self.save_email_recipients(to_list, cc_list)
    
    def remove_email_recipient(self, email: str, typ: str = 'to'):
        """Remove an email recipient"""
        to_list, cc_list = self.load_email_recipients()
        
        if typ == 'to':
            to_list = [e for e in to_list if e != email]
        elif typ == 'cc':
            cc_list = [e for e in cc_list if e != email]
        
        self.save_email_recipients(to_list, cc_list)
    
    def set_email_recipients(self, to_list: List[str], cc_list: List[str]):
        """Set all email recipients"""
        self.save_email_recipients(to_list, cc_list)
    
    def set_alert_template(self, subject: str, body: str):
        """Set alert template"""
        template = {"subject": subject, "body": body}
        self.save_alert_template(template)
    
    async def send_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        record_id: Optional[str] = None
    ):
        """Send an alert via configured channels"""
        
        # Check throttling
        alert_key = f"{alert_type}_{severity}_{message[:50]}"
        if self._is_throttled(alert_key):
            self.logger.info(f"Alert throttled: {alert_key}")
            return
        
        # Record alert sent
        self._record_alert_sent(alert_key)
        
        # Send via different channels
        await self._send_slack_notification(alert_type, severity, message, details)
        await self._send_email_notification(alert_type, severity, message, details, trace_id, record_id)
        
        # Store alert record
        await self._store_alert_record(alert_type, severity, message, details, trace_id, record_id)
    
    def _is_throttled(self, alert_key: str) -> bool:
        """Check if alert should be throttled"""
        if alert_key in self.alert_history:
            last_sent = self.alert_history[alert_key]
            throttle_minutes = self.settings.alert_throttle_minutes
            if datetime.now(timezone.utc) - last_sent < timedelta(minutes=throttle_minutes):
                return True
        return False
    
    def _record_alert_sent(self, alert_key: str):
        """Record that an alert was sent"""
        self.alert_history[alert_key] = datetime.now(timezone.utc)
    
    async def _send_slack_notification(
        self, 
        alert_type: AlertType, 
        severity: AlertSeverity,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Send Slack notification if configured"""
        if not self.settings.slack_webhook_url:
            self.logger.debug("Slack webhook not configured")
            return
        
        try:
            import requests
            
            # Prepare Slack message
            color_map = {
                AlertSeverity.LOW: "#36a64f",
                AlertSeverity.MEDIUM: "#ffa500", 
                AlertSeverity.HIGH: "#ff6b6b",
                AlertSeverity.CRITICAL: "#ff0000"
            }
            
            payload = {
                "channel": self.settings.slack_channel,
                "attachments": [{
                    "color": color_map.get(severity, "#36a64f"),
                    "title": f"🚨 {alert_type.value.replace('_', ' ').title()}",
                    "text": message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": severity.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Type", 
                            "value": alert_type.value,
                            "short": True
                        }
                    ],
                    "footer": "Indexing QA Alert System",
                    "ts": int(time.time())
                }]
            }
            
            if details:
                payload["attachments"][0]["fields"].append({
                    "title": "Details",
                    "value": json.dumps(details, indent=2),
                    "short": False
                })
            
            response = requests.post(self.settings.slack_webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            self.logger.info(f"Slack alert sent: {alert_type.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")
    
    async def _send_email_notification(
        self,
        alert_type: AlertType,
        severity: AlertSeverity, 
        message: str,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        record_id: Optional[str] = None
    ):
        """Send email notification with customizable template"""
        to_list, cc_list = self.load_email_recipients()
        
        if not to_list and not cc_list:
            self.logger.debug("No email recipients configured")
            return
        
        if not self.settings.email_username or not self.settings.email_password:
            self.logger.debug("Email credentials not configured")
            return
        
        try:
            # Load template
            template = self.load_alert_template()
            
            # Prepare template variables
            template_vars = {
                "alert_type": alert_type.value.replace('_', ' ').title(),
                "severity": severity.value.upper(),
                "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                "message": message,
                "record_id": record_id or "N/A",
                "trace_id": trace_id or "N/A",
                "details": json.dumps(details, indent=2) if details else "No additional details"
            }
            
            # Format subject and body using template
            subject = template["subject"].format(**template_vars)
            body = template["body"].format(**template_vars)
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.settings.email_username
            msg['To'] = ', '.join(to_list) if to_list else ''
            msg['Cc'] = ', '.join(cc_list) if cc_list else ''
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.settings.email_smtp_server, self.settings.email_smtp_port)
            server.starttls()
            server.login(self.settings.email_username, self.settings.email_password)
            
            all_recipients = to_list + cc_list
            server.sendmail(self.settings.email_username, all_recipients, msg.as_string())
            server.quit()
            
            self.logger.info(f"Email alert sent to {len(all_recipients)} recipients")
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
    
    async def _store_alert_record(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        record_id: Optional[str] = None
    ):
        """Store alert record in database"""
        try:
            with get_db_context() as db:
                alert_record = AlertRecord(
                    alert_type=alert_type.value,
                    severity=severity.value,
                    message=message,
                    details=details or {},
                    trace_id=trace_id,
                    record_id=record_id,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(alert_record)
                # commit is handled by the context manager
                
        except Exception as e:
            self.logger.error(f"Failed to store alert record: {e}")
    
    async def send_flagged_result_alert(
        self,
        check_name: str,
        failure_reason: str,
        trace_id: str,
        record_id: str,
        confidence_score: float,
        check_metadata: Optional[Dict[str, Any]] = None
    ):
        """Send alert for a flagged result"""
        message = f"Quality check '{check_name}' failed for record {record_id}"
        
        # Determine severity based on confidence score
        if confidence_score > 0.8:
            severity = AlertSeverity.HIGH
        elif confidence_score > 0.6:
            severity = AlertSeverity.MEDIUM
        else:
            severity = AlertSeverity.LOW
        
        details = {
            "check_name": check_name,
            "failure_reason": failure_reason,
            "confidence_score": confidence_score,
            "check_metadata": check_metadata or {}
        }
        
        await self.send_alert(
            alert_type=AlertType.QUALITY_THRESHOLD_EXCEEDED,
            severity=severity,
            message=message,
            details=details,
            trace_id=trace_id,
            record_id=record_id
        ) 
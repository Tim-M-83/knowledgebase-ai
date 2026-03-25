from pydantic import BaseModel


class LicenseStatusOut(BaseModel):
    license_enabled: bool
    license_active: bool
    license_status: str | None = None
    workspace_id: str | None = None
    instance_id_configured: bool = False
    license_key_configured: bool = False
    current_period_end: str | None = None
    last_validated_at: str | None = None
    grace_until: str | None = None
    last_error: str | None = None
    license_server_base_url: str
    remote_active_activation_count: int | None = None
    remote_total_activation_count: int | None = None
    activation_limit: int | None = None
    billing_email: str | None = None
    billing_email_source: str | None = None


class LicenseUrlOut(BaseModel):
    url: str


class LicenseActivateIn(BaseModel):
    license_key: str | None = None


class LicenseBillingEmailIn(BaseModel):
    billing_email: str | None = None

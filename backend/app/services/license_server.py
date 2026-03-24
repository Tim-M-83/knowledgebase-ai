from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import get_settings


settings = get_settings()


class LicenseServerError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class RemoteLicenseStatus:
    workspace_id: str
    subscription_status: str
    subscription_active: bool
    current_period_end: str | None = None
    last_synced_at: str | None = None
    last_error: str | None = None
    active_activation_count: int | None = None
    total_activation_count: int | None = None
    activation_limit: int | None = None


@dataclass
class RemoteActivateResponse:
    instance_id: str
    subscription_status: str
    subscription_active: bool
    current_period_end: str | None = None


@dataclass
class RemoteValidateResponse:
    allowed: bool
    status: str
    current_period_end: str | None = None


@dataclass
class RemoteResetActivationsResponse:
    workspace_id: str
    deactivated_count: int
    active_activation_count: int
    total_activation_count: int
    activation_limit: int
    subscription_status: str
    subscription_active: bool
    current_period_end: str | None = None
    last_synced_at: str | None = None
    last_error: str | None = None


def _json_headers() -> dict[str, str]:
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }


def _admin_headers() -> dict[str, str]:
    token = settings.effective_license_admin_token
    if not token:
        raise LicenseServerError('LICENSE_SERVER_ADMIN_TOKEN is not configured.', status_code=500)

    headers = _json_headers()
    headers['Authorization'] = f'Bearer {token}'
    return headers


def _base_url() -> str:
    base_url = settings.license_server_base_url.strip().rstrip('/')
    if not base_url:
        raise LicenseServerError('LICENSE_SERVER_BASE_URL is not configured.', status_code=500)
    return base_url


def _request(method: str, path: str, *, json: dict | None = None, admin_auth: bool = False) -> dict:
    headers = _admin_headers() if admin_auth else _json_headers()
    try:
        with httpx.Client(
            base_url=_base_url(),
            headers=headers,
            timeout=max(float(settings.license_request_timeout_seconds), 1.0),
        ) as client:
            response = client.request(method, path, json=json)
    except httpx.RequestError as exc:
        raise LicenseServerError(f'Unable to reach license server: {exc}') from exc

    if response.is_error:
        detail = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                candidate = payload.get('detail')
                if isinstance(candidate, str) and candidate.strip():
                    detail = candidate.strip()
        except Exception:
            detail = None
        if admin_auth and response.status_code == 401:
            raise LicenseServerError(
                'License server admin authentication failed. Update LICENSE_SERVER_ADMIN_TOKEN.',
                status_code=response.status_code,
            )
        raise LicenseServerError(detail or response.text or 'License server request failed.', status_code=response.status_code)

    try:
        payload = response.json()
    except Exception as exc:
        raise LicenseServerError('License server returned an invalid JSON response.') from exc
    if not isinstance(payload, dict):
        raise LicenseServerError('License server response payload was not an object.')
    return payload


def create_checkout_url(
    *,
    workspace_id: str,
    company_name: str | None = None,
    email: str | None = None,
) -> str:
    payload: dict[str, str] = {'workspace_id': workspace_id}
    if company_name:
        payload['company_name'] = company_name
    if email:
        payload['email'] = email

    data = _request('POST', '/billing/checkout', json=payload, admin_auth=True)
    checkout_url = str(data.get('checkout_url') or data.get('url') or '').strip()
    if not checkout_url:
        raise LicenseServerError('License server did not return a checkout URL.')
    return checkout_url


def fetch_remote_status(*, workspace_id: str) -> RemoteLicenseStatus:
    data = _request('GET', f'/license/status/{workspace_id}')
    return RemoteLicenseStatus(
        workspace_id=str(data.get('workspace_id') or workspace_id),
        subscription_status=str(data.get('subscription_status') or 'inactive'),
        subscription_active=bool(data.get('subscription_active')),
        current_period_end=str(data.get('current_period_end') or '').strip() or None,
        last_synced_at=str(data.get('last_synced_at') or '').strip() or None,
        last_error=str(data.get('last_error') or '').strip() or None,
        active_activation_count=int(data.get('active_activation_count')) if data.get('active_activation_count') is not None else None,
        total_activation_count=int(data.get('total_activation_count')) if data.get('total_activation_count') is not None else None,
        activation_limit=int(data.get('activation_limit')) if data.get('activation_limit') is not None else None,
    )


def activate_remote_license(
    *,
    workspace_id: str,
    company_name: str,
    email: str,
    license_key: str,
    machine_fingerprint: str,
    hostname: str | None,
) -> RemoteActivateResponse:
    payload = {
        'workspace_id': workspace_id,
        'company_name': company_name,
        'email': email,
        'license_key': license_key,
        'machine_fingerprint': machine_fingerprint,
        'hostname': hostname,
    }
    data = _request('POST', '/license/activate', json=payload)
    return RemoteActivateResponse(
        instance_id=str(data.get('instance_id') or '').strip(),
        subscription_status=str(data.get('subscription_status') or 'inactive'),
        subscription_active=bool(data.get('subscription_active')),
        current_period_end=str(data.get('current_period_end') or '').strip() or None,
    )


def validate_remote_license(
    *,
    workspace_id: str,
    license_key: str,
    instance_id: str,
    machine_fingerprint: str,
) -> RemoteValidateResponse:
    payload = {
        'workspace_id': workspace_id,
        'license_key': license_key,
        'instance_id': instance_id,
        'machine_fingerprint': machine_fingerprint,
    }
    data = _request('POST', '/license/validate', json=payload)
    return RemoteValidateResponse(
        allowed=bool(data.get('allowed')),
        status=str(data.get('status') or 'inactive'),
        current_period_end=str(data.get('current_period_end') or '').strip() or None,
    )


def deactivate_remote_license(
    *,
    workspace_id: str,
    license_key: str,
    instance_id: str,
) -> bool:
    payload = {
        'workspace_id': workspace_id,
        'license_key': license_key,
        'instance_id': instance_id,
    }
    data = _request('POST', '/license/deactivate', json=payload)
    return bool(data.get('deactivated'))


def sync_remote_customer(*, workspace_id: str) -> RemoteLicenseStatus:
    data = _request('POST', '/billing/sync', json={'workspace_id': workspace_id}, admin_auth=True)
    return RemoteLicenseStatus(
        workspace_id=str(data.get('workspace_id') or workspace_id),
        subscription_status=str(data.get('subscription_status') or 'inactive'),
        subscription_active=bool(data.get('subscription_active')),
        current_period_end=str(data.get('current_period_end') or '').strip() or None,
        last_synced_at=str(data.get('last_synced_at') or '').strip() or None,
        last_error=str(data.get('last_error') or '').strip() or None,
    )


def reset_remote_activations(*, workspace_id: str) -> RemoteResetActivationsResponse:
    data = _request('POST', '/billing/reset-activations', json={'workspace_id': workspace_id}, admin_auth=True)
    return RemoteResetActivationsResponse(
        workspace_id=str(data.get('workspace_id') or workspace_id),
        deactivated_count=int(data.get('deactivated_count') or 0),
        active_activation_count=int(data.get('active_activation_count') or 0),
        total_activation_count=int(data.get('total_activation_count') or 0),
        activation_limit=int(data.get('activation_limit') or 0),
        subscription_status=str(data.get('subscription_status') or 'inactive'),
        subscription_active=bool(data.get('subscription_active')),
        current_period_end=str(data.get('current_period_end') or '').strip() or None,
        last_synced_at=str(data.get('last_synced_at') or '').strip() or None,
        last_error=str(data.get('last_error') or '').strip() or None,
    )

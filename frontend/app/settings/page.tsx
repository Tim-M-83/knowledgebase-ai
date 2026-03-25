'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { api } from '@/lib/api';
import { getCurrentUser } from '@/lib/auth';
import {
  Health,
  LicenseStatus,
  OllamaTestResult,
  OpenAITestResult,
  ProviderRuntime,
  ProviderSettings,
  ProviderSettingsUpdate,
  User,
} from '@/lib/types';

type DataSettings = { retention_days: number; max_upload_mb: number; email_helper_enabled: boolean };
type FeedbackTone = 'success' | 'error' | 'info';
type FeedbackState = { tone: FeedbackTone; text: string };

function FeedbackBanner({ feedback }: { feedback: FeedbackState }) {
  const palette =
    feedback.tone === 'success'
      ? 'border-green-200 bg-green-50 text-green-800'
      : feedback.tone === 'error'
        ? 'border-red-200 bg-red-50 text-red-800'
        : 'border-slate-200 bg-slate-50 text-slate-700';

  return (
    <div className={`rounded-2xl border px-3 py-3 text-sm ${palette}`}>
      <div className='flex items-start gap-2'>
        <span className='mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center' aria-hidden='true'>
          {feedback.tone === 'success' ? (
            <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2' className='h-4 w-4'>
              <path d='M20 6 9 17l-5-5' />
            </svg>
          ) : feedback.tone === 'error' ? (
            <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2' className='h-4 w-4'>
              <path d='M12 9v4' />
              <path d='M12 17h.01' />
              <path d='M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z' />
            </svg>
          ) : (
            <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2' className='h-4 w-4'>
              <circle cx='12' cy='12' r='10' />
              <path d='M12 16v-4' />
              <path d='M12 8h.01' />
            </svg>
          )}
        </span>
        <p>{feedback.text}</p>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const router = useRouter();
  const [health, setHealth] = useState<Health | null>(null);
  const [providerSettings, setProviderSettings] = useState<ProviderSettings | null>(null);
  const [licenseStatus, setLicenseStatus] = useState<LicenseStatus | null>(null);
  const [dataSettings, setDataSettings] = useState<DataSettings | null>(null);
  const [currentRole, setCurrentRole] = useState<'admin' | 'editor' | 'viewer' | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  const [provider, setProvider] = useState<ProviderRuntime>('openai');
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState('');
  const [ollamaChatModel, setOllamaChatModel] = useState('');
  const [ollamaEmbeddingsModel, setOllamaEmbeddingsModel] = useState('');
  const [openaiApiKey, setOpenaiApiKey] = useState('');

  const [message, setMessage] = useState('');
  const [licenseFeedback, setLicenseFeedback] = useState<FeedbackState | null>(null);
  const [diagnosticsFeedback, setDiagnosticsFeedback] = useState<FeedbackState | null>(null);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [licenseKeyInput, setLicenseKeyInput] = useState('');
  const [billingEmailInput, setBillingEmailInput] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmNewPassword, setShowConfirmNewPassword] = useState(false);
  const [showLicenseKey, setShowLicenseKey] = useState(false);
  const [testingOpenAI, setTestingOpenAI] = useState(false);
  const [testingOllama, setTestingOllama] = useState(false);
  const [savingProvider, setSavingProvider] = useState(false);
  const [savingData, setSavingData] = useState(false);
  const [savingCredentials, setSavingCredentials] = useState(false);
  const [deletingOpenAIKey, setDeletingOpenAIKey] = useState(false);
  const [startingCheckout, setStartingCheckout] = useState(false);
  const [activatingLicense, setActivatingLicense] = useState(false);
  const [validatingLicense, setValidatingLicense] = useState(false);
  const [deactivatingLicense, setDeactivatingLicense] = useState(false);
  const [resettingActivations, setResettingActivations] = useState(false);
  const [savingBillingEmail, setSavingBillingEmail] = useState(false);
  const [exportingLogs, setExportingLogs] = useState(false);

  const canSaveProvider = currentRole === 'admin';
  const canSaveData = currentRole === 'admin';

  const PasswordToggleButton = ({
    shown,
    onToggle,
    label
  }: {
    shown: boolean;
    onToggle: () => void;
    label: string;
  }) => (
    <button
      type='button'
      onClick={onToggle}
      aria-label={shown ? `Hide ${label}` : `Show ${label}`}
      title={shown ? `Hide ${label}` : `Show ${label}`}
      className='absolute inset-y-0 right-3 flex items-center text-slate-400 transition hover:text-slate-600'
    >
      <svg
        viewBox='0 0 24 24'
        fill='none'
        stroke='currentColor'
        strokeWidth='1.8'
        strokeLinecap='round'
        strokeLinejoin='round'
        className='h-4 w-4'
        aria-hidden='true'
      >
        <path d='M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z' />
        <circle cx='12' cy='12' r='3' />
        {shown ? null : <path d='M4 4l16 16' />}
      </svg>
    </button>
  );

  const reloadLicenseStatus = async () => {
    const updated = await api.get<LicenseStatus>('/license/status');
    setLicenseStatus(updated);
    return updated;
  };

  const formatLicenseActionError = (prefix: string, error: Error) => {
    const detail = error.message || 'Unknown license error.';
    if (detail.includes('already linked to another Workspace ID on Polar')) {
      return `${prefix}: ${detail} Restore the original LICENSE_WORKSPACE_ID to reuse the existing purchase, or save a different billing email below before starting a new checkout for this workspace.`;
    }
    if (detail.includes('Activation limit reached for this workspace.')) {
      return `${prefix}: ${detail} This workspace is already using all allowed activation slots. Use "Reset All Activations" below, then try activating again.`;
    }
    if (detail.includes('License key does not match this workspace.')) {
      return `${prefix}: ${detail} This usually means the billing email or purchase is already linked on Polar to a different Workspace ID. Restore the original Workspace ID in .env as LICENSE_WORKSPACE_ID, rebuild the API, and then activate again. Otherwise save a different billing email below and start a new checkout for the Workspace ID shown here.`;
    }
    if (detail.includes('demo/test domain')) {
      return `${prefix}: ${detail}`;
    }
    if (detail.includes('No billing email is configured.')) {
      return `${prefix}: ${detail}`;
    }
    if (detail.includes('customer_email') && detail.includes('valid email address')) {
      return `${prefix}: Polar rejected the billing email for this checkout. Save a real reachable billing email below and then try again.`;
    }
    return `${prefix}: ${detail}`;
  };

  const isRejectedBillingEmail = (email: string | null | undefined) => {
    const normalized = (email || '').trim().toLowerCase();
    if (!normalized || !normalized.includes('@')) {
      return false;
    }

    const domain = normalized.split('@').pop() || '';
    return (
      !domain.includes('.') ||
      domain === 'example.com' ||
      domain === 'example.org' ||
      domain === 'example.net' ||
      domain === 'localhost' ||
      domain.endsWith('.local') ||
      domain.endsWith('.test')
    );
  };

  const billingEmailSourceLabel = (source: LicenseStatus['billing_email_source']) => {
    if (source === 'saved') return 'saved billing email';
    if (source === 'env') return '.env LICENSE_BILLING_EMAIL';
    if (source === 'admin') return 'current admin login email';
    return 'not configured';
  };

  const copyWorkspaceId = async () => {
    const workspaceId = licenseStatus?.workspace_id?.trim();
    if (!workspaceId) {
      setLicenseFeedback({ tone: 'error', text: 'No Workspace ID is available yet.' });
      return;
    }

    try {
      await navigator.clipboard.writeText(workspaceId);
      setLicenseFeedback({
        tone: 'info',
        text: 'Workspace ID copied. Keep this exact value if you ever reinstall and want to restore the same licensed workspace.',
      });
    } catch {
      setLicenseFeedback({
        tone: 'error',
        text: 'Could not copy the Workspace ID automatically. Copy it manually from the value shown below.',
      });
    }
  };

  const load = async () => {
    const me = await getCurrentUser();
    setCurrentUser(me);
    setCurrentRole(me?.role ?? null);
    if (!me) {
      router.replace('/login');
      return;
    }
    if (me.must_change_credentials) {
      return;
    }

    const [healthData, providerData, settingsData] = await Promise.all([
      api.get<Health>('/health'),
      api.get<ProviderSettings>('/settings/providers'),
      api.get<DataSettings>('/settings/data'),
      reloadLicenseStatus()
    ]);
    setHealth(healthData);
    setProviderSettings(providerData);
    setDataSettings(settingsData);
    setProvider(providerData.llm_provider);
    setOllamaBaseUrl(providerData.ollama_base_url);
    setOllamaChatModel(providerData.ollama_chat_model);
    setOllamaEmbeddingsModel(providerData.ollama_embeddings_model);
  };

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  useEffect(() => {
    setBillingEmailInput(licenseStatus?.billing_email || '');
  }, [licenseStatus?.billing_email]);

  const availableProviders = useMemo(
    () => providerSettings?.available_providers ?? (['openai', 'ollama'] as ProviderRuntime[]),
    [providerSettings]
  );

  const billingEmailWarning = useMemo(() => {
    if (!licenseStatus) {
      return null;
    }

    const effectiveEmail = (licenseStatus.billing_email || '').trim();
    if (!effectiveEmail) {
      return 'No billing email is configured yet. Save a real reachable billing email below before starting checkout.';
    }

    if (isRejectedBillingEmail(effectiveEmail)) {
      return `The current billing email from ${billingEmailSourceLabel(licenseStatus.billing_email_source)} is a demo/test or otherwise invalid checkout address, and Polar will reject it. Save a real reachable billing email below first.`;
    }

    return null;
  }, [licenseStatus]);

  const checkoutBlockedByBillingEmail = Boolean(billingEmailWarning);

  const testOpenAI = async () => {
    setTestingOpenAI(true);
    setMessage('');
    try {
      const result = await api.post<OpenAITestResult>(
        '/settings/providers/test-openai',
        openaiApiKey.trim() ? { openai_api_key: openaiApiKey.trim() } : {},
        false
      );
      setMessage(`OpenAI test passed. Chat: ${result.chat_endpoint_ok}, Embeddings: ${result.embeddings_endpoint_ok}`);
    } catch (error) {
      setMessage(`OpenAI test failed: ${(error as Error).message}`);
    } finally {
      setTestingOpenAI(false);
    }
  };

  const testOllama = async () => {
    setTestingOllama(true);
    setMessage('');
    try {
      const result = await api.post<OllamaTestResult>(
        '/settings/providers/test-ollama',
        {
          ollama_base_url: ollamaBaseUrl.trim(),
          ollama_chat_model: ollamaChatModel.trim(),
          ollama_embeddings_model: ollamaEmbeddingsModel.trim()
        },
        false
      );
      setMessage(
        `Ollama test passed. Chat: ${result.chat_endpoint_ok}, Embeddings: ${result.embeddings_endpoint_ok}` +
          (result.embedding_dimension ? `, Dimension: ${result.embedding_dimension}` : '')
      );
    } catch (error) {
      setMessage(`Ollama test failed: ${(error as Error).message}`);
    } finally {
      setTestingOllama(false);
    }
  };

  const saveProviderSettings = async () => {
    if (!canSaveProvider) {
      setMessage('Only admins can save provider settings.');
      return;
    }

    setSavingProvider(true);
    setMessage('');
    try {
      const payload: ProviderSettingsUpdate = {
        llm_provider: provider,
        embeddings_provider: provider,
        ollama_base_url: ollamaBaseUrl.trim(),
        ollama_chat_model: ollamaChatModel.trim(),
        ollama_embeddings_model: ollamaEmbeddingsModel.trim()
      };
      if (openaiApiKey.trim()) {
        payload.openai_api_key = openaiApiKey.trim();
      }
      const updated = await api.put<ProviderSettings>('/settings/providers', payload, true);
      setProviderSettings(updated);
      setOpenaiApiKey('');
      setMessage(updated.warning || 'Provider settings saved successfully.');
      const healthData = await api.get<Health>('/health');
      setHealth(healthData);
    } catch (error) {
      setMessage(`Failed to save provider settings: ${(error as Error).message}`);
    } finally {
      setSavingProvider(false);
    }
  };

  const deleteOpenAIKey = async () => {
    if (!canSaveProvider) {
      setMessage('Only admins can delete provider API keys.');
      return;
    }
    const confirmed = window.confirm(
      'Delete the configured OpenAI API key? OpenAI will remain disabled until a new key is saved.'
    );
    if (!confirmed) return;

    setDeletingOpenAIKey(true);
    setMessage('');
    try {
      const updated = await api.delete<ProviderSettings>('/settings/providers/openai-key', true);
      setProviderSettings(updated);
      setOpenaiApiKey('');
      const healthData = await api.get<Health>('/health');
      setHealth(healthData);
      setMessage('OpenAI API key deleted. Enter a new key to re-enable OpenAI.');
    } catch (error) {
      setMessage(`Failed to delete OpenAI API key: ${(error as Error).message}`);
    } finally {
      setDeletingOpenAIKey(false);
    }
  };

  const saveDataSettings = async () => {
    if (!dataSettings) return;
    if (!canSaveData) {
      setMessage('Only admins can save data settings.');
      return;
    }
    setSavingData(true);
    setMessage('');
    try {
      await api.put('/settings/data', dataSettings, true);
      setMessage('Data settings updated.');
    } catch (error) {
      setMessage(`Failed to update data settings: ${(error as Error).message}`);
    } finally {
      setSavingData(false);
    }
  };

  const validateLicense = async ({ silent }: { silent: boolean }) => {
    if (!canSaveProvider) {
      if (!silent) {
        setLicenseFeedback({ tone: 'error', text: 'Only admins can validate this installation.' });
      }
      return;
    }
    if (!licenseStatus?.license_key_configured) {
      if (!silent) {
        setLicenseFeedback({
          tone: 'error',
          text: 'No Polar license key is stored yet. Paste the key from the hosted checkout success page first.'
        });
      }
      return;
    }
    setValidatingLicense(true);
    if (!silent) {
      setLicenseFeedback(null);
    }
    try {
      const updated = await api.post<LicenseStatus>('/license/validate', {}, true);
      setLicenseStatus(updated);
      if (!silent) {
        setLicenseFeedback({ tone: 'success', text: 'Installation validated successfully.' });
      }
    } catch (error) {
      try {
        await reloadLicenseStatus();
      } catch {}
      if (!silent) {
        setLicenseFeedback({ tone: 'error', text: `Installation validation failed: ${(error as Error).message}` });
      }
    } finally {
      setValidatingLicense(false);
    }
  };

  const saveBillingEmail = async () => {
    if (!canSaveProvider) {
      setLicenseFeedback({ tone: 'error', text: 'Only admins can save the billing email.' });
      return;
    }

    setSavingBillingEmail(true);
    setLicenseFeedback(null);
    try {
      const updated = await api.put<LicenseStatus>(
        '/license/billing-email',
        { billing_email: billingEmailInput.trim() || '' },
        true
      );
      setLicenseStatus(updated);
      setLicenseFeedback({
        tone: 'success',
        text: billingEmailInput.trim()
          ? 'Billing email saved. Polar checkout and activation will use this address.'
          : updated.billing_email
            ? `Saved billing email cleared. The app will now fall back to ${billingEmailSourceLabel(updated.billing_email_source)}.`
            : 'Saved billing email cleared.',
      });
    } catch (error) {
      setLicenseFeedback({
        tone: 'error',
        text: formatLicenseActionError('Failed to save billing email', error as Error),
      });
    } finally {
      setSavingBillingEmail(false);
    }
  };

  const startCheckout = async () => {
    if (!canSaveProvider) {
      setLicenseFeedback({ tone: 'error', text: 'Only admins can start checkout.' });
      return;
    }
    if (checkoutBlockedByBillingEmail) {
      setLicenseFeedback({ tone: 'error', text: billingEmailWarning || 'Save a valid billing email first.' });
      return;
    }
    setStartingCheckout(true);
    setLicenseFeedback(null);
    try {
      const response = await api.post<{ url: string }>('/license/checkout', {}, true);
      window.location.assign(response.url);
    } catch (error) {
      setLicenseFeedback({ tone: 'error', text: formatLicenseActionError('Failed to start checkout', error as Error) });
    } finally {
      setStartingCheckout(false);
    }
  };

  const activateLicense = async () => {
    if (!canSaveProvider) {
      setLicenseFeedback({ tone: 'error', text: 'Only admins can activate this installation.' });
      return;
    }
    if (checkoutBlockedByBillingEmail) {
      setLicenseFeedback({ tone: 'error', text: billingEmailWarning || 'Save a valid billing email first.' });
      return;
    }
    const normalizedLicenseKey = licenseKeyInput.trim();
    if (!normalizedLicenseKey && !licenseStatus?.license_key_configured) {
      setLicenseFeedback({
        tone: 'error',
        text: 'Paste the Polar license key from the hosted checkout success page before activating this installation.'
      });
      return;
    }
    setActivatingLicense(true);
    setLicenseFeedback(null);
    try {
      const updated = await api.post<LicenseStatus>(
        '/license/activate',
        normalizedLicenseKey ? { license_key: normalizedLicenseKey } : {},
        true
      );
      setLicenseStatus(updated);
      setLicenseKeyInput('');
      setLicenseFeedback({
        tone: 'success',
        text: normalizedLicenseKey
          ? 'Installation activated successfully. The Polar license key is now stored securely for future validation.'
          : 'Installation activated successfully.'
      });
    } catch (error) {
      try {
        await reloadLicenseStatus();
      } catch {}
      setLicenseFeedback({
        tone: 'error',
        text: formatLicenseActionError('Installation activation failed', error as Error),
      });
    } finally {
      setActivatingLicense(false);
    }
  };

  const deactivateLicense = async () => {
    if (!canSaveProvider) {
      setLicenseFeedback({ tone: 'error', text: 'Only admins can deactivate this installation.' });
      return;
    }
    if (!licenseStatus?.license_key_configured) {
      setLicenseFeedback({
        tone: 'error',
        text: 'No Polar license key is stored yet. Paste the key first if you need to replace or recover this installation.'
      });
      return;
    }
    const confirmed = window.confirm('Deactivate the current local license activation for this installation?');
    if (!confirmed) {
      return;
    }
    setDeactivatingLicense(true);
    setLicenseFeedback(null);
    try {
      const updated = await api.post<LicenseStatus>('/license/deactivate', {}, true);
      setLicenseStatus(updated);
      setLicenseFeedback({
        tone: 'success',
        text: 'Local installation activation removed. The stored Polar license key was kept so you can reactivate quickly if needed.'
      });
    } catch (error) {
      try {
        await reloadLicenseStatus();
      } catch {}
      setLicenseFeedback({ tone: 'error', text: `Failed to deactivate license: ${(error as Error).message}` });
    } finally {
      setDeactivatingLicense(false);
    }
  };

  const resetActivations = async () => {
    if (!canSaveProvider) {
      setLicenseFeedback({ tone: 'error', text: 'Only admins can reset workspace activations.' });
      return;
    }
    const confirmed = window.confirm(
      'Reset all active activations for this workspace? This revokes every currently active installation and lets you activate this installation again.'
    );
    if (!confirmed) {
      return;
    }

    setResettingActivations(true);
    setLicenseFeedback(null);
    try {
      const updated = await api.post<LicenseStatus>('/license/reset-activations', {}, true);
      setLicenseStatus(updated);
      setLicenseFeedback({
        tone: 'success',
        text: 'All active workspace activations were reset. You can now activate this installation again.',
      });
    } catch (error) {
      try {
        await reloadLicenseStatus();
      } catch {}
      setLicenseFeedback({
        tone: 'error',
        text: formatLicenseActionError('Failed to reset activations', error as Error),
      });
    } finally {
      setResettingActivations(false);
    }
  };

  const saveCredentials = async () => {
    const normalizedCurrentPassword = currentPassword.trim();
    const normalizedNewEmail = newEmail.trim();
    const normalizedNewPassword = newPassword.trim();
    const normalizedConfirmPassword = confirmNewPassword.trim();
    const mustChangeCredentials = Boolean(currentUser?.must_change_credentials);

    setMessage('');
    if (!mustChangeCredentials && !normalizedCurrentPassword) {
      setMessage('Current password is required.');
      return;
    }
    if (mustChangeCredentials && (!normalizedNewEmail || !normalizedNewPassword)) {
      setMessage('Initial security setup requires both a new email and a new password.');
      return;
    }
    if (!normalizedNewEmail && !normalizedNewPassword) {
      setMessage('Provide a new email, a new password, or both.');
      return;
    }
    if (normalizedNewPassword && normalizedNewPassword !== normalizedConfirmPassword) {
      setMessage('New password and confirmation do not match.');
      return;
    }

    setSavingCredentials(true);
    try {
      await api.put<{ message: string }>(
        '/auth/me/credentials',
        {
          ...(!mustChangeCredentials && normalizedCurrentPassword ? { current_password: normalizedCurrentPassword } : {}),
          ...(normalizedNewEmail ? { new_email: normalizedNewEmail } : {}),
          ...(normalizedNewPassword ? { new_password: normalizedNewPassword } : {}),
        },
        true
      );
      setCurrentPassword('');
      setNewEmail('');
      setNewPassword('');
      setConfirmNewPassword('');
      setMessage('Credentials updated successfully. Redirecting to login...');
      window.setTimeout(() => {
        router.replace('/login');
      }, 900);
    } catch (error) {
      setMessage(`Failed to update credentials: ${(error as Error).message}`);
    } finally {
      setSavingCredentials(false);
    }
  };

  const exportSupportLogs = async () => {
    if (!canSaveProvider) {
      setDiagnosticsFeedback({ tone: 'error', text: 'Only admins can export support diagnostics.' });
      return;
    }

    setExportingLogs(true);
    setDiagnosticsFeedback(null);

    try {
      const response = await fetch(`${api.baseUrl}/settings/log-export`, {
        method: 'GET',
        credentials: 'include',
      });

      if (!response.ok) {
        const raw = await response.text();
        try {
          const parsed = JSON.parse(raw);
          const detail = typeof parsed?.detail === 'string' ? parsed.detail : raw;
          throw new Error(detail || `Request failed: ${response.status}`);
        } catch {
          throw new Error(raw || `Request failed: ${response.status}`);
        }
      }

      const blob = await response.blob();
      const disposition = response.headers.get('content-disposition') || '';
      const filenameMatch = disposition.match(/filename="?([^"]+)"?/i);
      const filename = filenameMatch?.[1] || 'kbai-support-logs.zip';
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      setDiagnosticsFeedback({
        tone: 'success',
        text: 'Support log export downloaded successfully.',
      });
    } catch (error) {
      setDiagnosticsFeedback({
        tone: 'error',
        text: `Failed to export support logs: ${(error as Error).message}`,
      });
    } finally {
      setExportingLogs(false);
    }
  };

  return (
    <div className='space-y-4'>
      <Card>
        <h2 className='text-sm font-semibold'>Account Security</h2>
        {currentUser?.must_change_credentials ? (
          <div className='mt-3 rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900'>
            <p className='font-semibold'>Initial Security Setup</p>
            <p className='mt-1'>
              This installation was created with a one-time bootstrap admin. Before using the rest of the app, set
              your real email address and choose a new password here. You do not need to enter the previous password
              during this first-time setup.
            </p>
          </div>
        ) : (
          <p className='mt-2 text-xs text-slate-500'>
            Update your own login email and password. Current password is required for confirmation.
          </p>
        )}
        <div className='mt-3 grid gap-3 md:grid-cols-2'>
          {currentUser?.must_change_credentials ? null : (
            <div className='space-y-2'>
              <label className='text-xs text-slate-500'>Current Password</label>
              <Input
                type='password'
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder='Enter current password'
              />
            </div>
          )}
          <div className='space-y-2'>
            <label className='text-xs text-slate-500'>
              New Email {currentUser?.must_change_credentials ? '(required)' : '(optional)'}
            </label>
            <Input
              type='email'
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              placeholder='new-email@example.com'
            />
          </div>
          <div className='space-y-2'>
            <label className='text-xs text-slate-500'>
              New Password {currentUser?.must_change_credentials ? '(required)' : '(optional)'}
            </label>
            <div className='relative'>
              <Input
                type={showNewPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder='Enter a new password'
                className='pr-10'
              />
              <PasswordToggleButton
                shown={showNewPassword}
                onToggle={() => setShowNewPassword((value) => !value)}
                label='new password'
              />
            </div>
          </div>
          <div className='space-y-2'>
            <label className='text-xs text-slate-500'>Confirm New Password</label>
            <div className='relative'>
              <Input
                type={showConfirmNewPassword ? 'text' : 'password'}
                value={confirmNewPassword}
                onChange={(e) => setConfirmNewPassword(e.target.value)}
                placeholder='Repeat new password'
                className='pr-10'
              />
              <PasswordToggleButton
                shown={showConfirmNewPassword}
                onToggle={() => setShowConfirmNewPassword((value) => !value)}
                label='password confirmation'
              />
            </div>
          </div>
        </div>
        <div className='mt-3'>
          <Button onClick={saveCredentials} disabled={savingCredentials}>
            {savingCredentials
              ? 'Updating...'
              : currentUser?.must_change_credentials
                ? 'Complete Initial Security Setup'
                : 'Update Credentials'}
          </Button>
        </div>
      </Card>

      {currentUser?.must_change_credentials ? null : (
        <>
      <Card>
        <h2 className='text-sm font-semibold'>Provider Settings</h2>
        {providerSettings ? (
          <div className='mt-3 space-y-1 text-sm text-slate-600'>
            <p>LLM Provider: {providerSettings.llm_provider}</p>
            <p>Embeddings Provider: {providerSettings.embeddings_provider}</p>
            <p>OpenAI Chat Model: {providerSettings.openai_chat_model}</p>
            <p>OpenAI Embeddings Model: {providerSettings.openai_embeddings_model}</p>
            <p>Ollama Base URL: {providerSettings.ollama_base_url}</p>
            <p>Ollama Chat Model: {providerSettings.ollama_chat_model}</p>
            <p>Ollama Embeddings Model: {providerSettings.ollama_embeddings_model}</p>
            <p>
              OpenAI Key: {providerSettings.openai_api_key_configured ? providerSettings.openai_api_key_masked : 'Not configured'}
            </p>
            {providerSettings.warning ? <p className='text-amber-700'>{providerSettings.warning}</p> : null}
          </div>
        ) : null}
      </Card>

      <Card>
        <h2 className='text-sm font-semibold'>Runtime Provider</h2>
        <div className='mt-3 grid gap-3 md:grid-cols-2'>
          <div className='space-y-2'>
            <label className='text-xs text-slate-500'>Provider</label>
            <Select value={provider} onChange={(e) => setProvider(e.target.value as ProviderRuntime)}>
              {availableProviders.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </Select>
          </div>
          <div className='space-y-2'>
            <label className='text-xs text-slate-500'>OpenAI API Key (optional update)</label>
            <Input
              placeholder='sk-...'
              type='password'
              value={openaiApiKey}
              onChange={(e) => setOpenaiApiKey(e.target.value)}
            />
          </div>
          <div className='space-y-2'>
            <label className='text-xs text-slate-500'>Ollama Base URL</label>
            <Input
              placeholder='http://host.docker.internal:11434'
              value={ollamaBaseUrl}
              onChange={(e) => setOllamaBaseUrl(e.target.value)}
            />
          </div>
          <div className='space-y-2'>
            <label className='text-xs text-slate-500'>Ollama Chat Model</label>
            <Input value={ollamaChatModel} onChange={(e) => setOllamaChatModel(e.target.value)} />
          </div>
          <div className='space-y-2'>
            <label className='text-xs text-slate-500'>Ollama Embeddings Model</label>
            <Input value={ollamaEmbeddingsModel} onChange={(e) => setOllamaEmbeddingsModel(e.target.value)} />
          </div>
        </div>
        <div className='mt-3 flex flex-wrap gap-2'>
          <Button onClick={saveProviderSettings} disabled={!canSaveProvider || savingProvider}>
            {savingProvider ? 'Saving...' : 'Save Provider Settings'}
          </Button>
          {canSaveProvider ? (
            <Button variant='secondary' onClick={deleteOpenAIKey} disabled={deletingOpenAIKey}>
              {deletingOpenAIKey ? 'Deleting OpenAI key...' : 'Delete OpenAI API Key'}
            </Button>
          ) : null}
          <Button variant='secondary' onClick={testOpenAI} disabled={testingOpenAI}>
            {testingOpenAI ? 'Testing OpenAI...' : 'Test OpenAI'}
          </Button>
          <Button variant='secondary' onClick={testOllama} disabled={testingOllama}>
            {testingOllama ? 'Testing Ollama...' : 'Test Ollama'}
          </Button>
        </div>
        <p className='mt-2 text-xs text-slate-500'>
          Runtime switching takes effect for new requests immediately. Only admins can save provider settings.
        </p>
        {canSaveProvider && licenseStatus ? (
          <div className='mt-4 rounded-2xl border border-slate-200 bg-white p-3 text-xs text-slate-600'>
            <p className='font-semibold text-slate-700'>License &amp; Subscription</p>
            <div className='mt-2 space-y-1'>
              <p>License enforcement enabled: {licenseStatus.license_enabled ? 'Yes' : 'No'}</p>
              <p>Local license active: {licenseStatus.license_active ? 'Yes' : 'No'}</p>
              <p>Status: {licenseStatus.license_status || 'unknown'}</p>
              <div className='flex flex-wrap items-center gap-2'>
                <p>Workspace ID: {licenseStatus.workspace_id || 'Not available yet'}</p>
                {licenseStatus.workspace_id ? (
                  <button
                    type='button'
                    onClick={copyWorkspaceId}
                    className='inline-flex items-center justify-center rounded-full border border-slate-300 bg-white px-3 py-1 text-[11px] font-medium text-slate-700 transition hover:bg-slate-50'
                  >
                    Copy Workspace ID
                  </button>
                ) : null}
              </div>
              <p>Local activation stored: {licenseStatus.instance_id_configured ? 'Yes' : 'No'}</p>
              <p>Polar license key stored: {licenseStatus.license_key_configured ? 'Yes' : 'No'}</p>
              {licenseStatus.activation_limit ? (
                <p>
                  Active activations: {licenseStatus.remote_active_activation_count ?? 0} / {licenseStatus.activation_limit}
                </p>
              ) : null}
              {licenseStatus.remote_total_activation_count !== undefined && licenseStatus.remote_total_activation_count !== null ? (
                <p>Total activations recorded: {licenseStatus.remote_total_activation_count}</p>
              ) : null}
              <p>Billing email: {licenseStatus.billing_email || 'Not configured yet'}</p>
              <p>Billing email source: {billingEmailSourceLabel(licenseStatus.billing_email_source)}</p>
              <p>License server: {licenseStatus.license_server_base_url}</p>
              {licenseStatus.current_period_end ? <p>Current period end: {licenseStatus.current_period_end}</p> : null}
              {licenseStatus.last_validated_at ? <p>Last validation: {licenseStatus.last_validated_at}</p> : null}
              {licenseStatus.grace_until ? <p>Grace until: {licenseStatus.grace_until}</p> : null}
              {licenseStatus.last_error ? <p className='text-red-700'>Last error: {licenseStatus.last_error}</p> : null}
            </div>
            <div className='mt-3 rounded-2xl border border-amber-200 bg-amber-50 px-3 py-3 text-[11px] text-amber-900'>
              <p className='font-semibold text-amber-950'>Reinstall Recovery</p>
              <p className='mt-1'>
                This Workspace ID is the license anchor for this installation. If you reinstall and want to reuse the
                same Polar purchase, restore this exact value in <code>.env</code> as{' '}
                <code>LICENSE_WORKSPACE_ID</code>, rebuild the API, and then activate with the same Polar key.
              </p>
              <p className='mt-1'>
                A stored Polar license key does not automatically prove it matches the Workspace ID shown above. Old
                keys continue to work only for the workspace they were originally issued for.
              </p>
            </div>
            <div className='mt-3 space-y-2'>
              <label className='text-xs font-medium text-slate-600'>Billing Email</label>
              <Input
                type='email'
                value={billingEmailInput}
                onChange={(e) => setBillingEmailInput(e.target.value)}
                placeholder='billing@your-company.com'
              />
              <p className='text-[11px] text-slate-500'>
                Used for Polar checkout and activation. Use a real reachable address. Demo domains like{' '}
                <code>example.com</code> will be rejected.
              </p>
              <p className='text-[11px] text-slate-500'>
                Your admin login email can be different. Subscription checkout and the Polar customer portal use the
                billing email shown here.
              </p>
              <p className='text-[11px] text-slate-500'>
                Under the current restore policy, one billing email effectively tracks one licensed workspace on Polar.
                If this email was already used for an older workspace, restore that original Workspace ID or use a
                different billing email for a brand new workspace purchase.
              </p>
              <div className='flex flex-wrap gap-2'>
                <Button variant='secondary' onClick={saveBillingEmail} disabled={savingBillingEmail}>
                  {savingBillingEmail ? 'Saving billing email...' : 'Save Billing Email'}
                </Button>
              </div>
            </div>
            {billingEmailWarning ? (
              <div className='mt-3'>
                <FeedbackBanner feedback={{ tone: 'error', text: billingEmailWarning }} />
              </div>
            ) : null}
            {licenseFeedback ? (
              <div className='mt-3'>
                <FeedbackBanner feedback={licenseFeedback} />
              </div>
            ) : null}
            <div className='mt-3 space-y-2'>
              <label className='text-xs font-medium text-slate-600'>Polar License Key</label>
              <div className='relative'>
                <Input
                  type={showLicenseKey ? 'text' : 'password'}
                  value={licenseKeyInput}
                  onChange={(e) => setLicenseKeyInput(e.target.value)}
                  placeholder='Paste the Polar-generated license key'
                  className='pr-10'
                />
                <PasswordToggleButton
                  shown={showLicenseKey}
                  onToggle={() => setShowLicenseKey((value) => !value)}
                  label='license key'
                />
              </div>
              <p className='text-[11px] text-slate-500'>
                1. Click <span className='font-medium'>Buy / Renew Subscription</span> to start the 7-day free trial.
                2. Complete checkout on the external license server. 3. Copy the Polar-generated license key from the
                hosted success page. 4. Paste it here and activate this installation.
              </p>
              <p className='text-[11px] text-slate-500'>
                If you are restoring an existing paid workspace after a reinstall, first restore the original{' '}
                <code>LICENSE_WORKSPACE_ID</code> in your local <code>.env</code> and rebuild the API. Otherwise a key
                from the old workspace will be rejected as a mismatch.
              </p>
            </div>
            <div className='mt-3 space-y-2'>
              <label className='text-xs font-medium text-slate-600'>Installation Activation</label>
              <Button variant='secondary' onClick={activateLicense} disabled={activatingLicense || checkoutBlockedByBillingEmail}>
                {activatingLicense ? 'Activating...' : 'Activate This Installation'}
              </Button>
              <p className='text-[11px] text-slate-500'>
                Activation stores the current local instance and reuses the encrypted Polar license key for future
                validation and recovery.
              </p>
              <p className='text-[11px] text-slate-500'>
                If this workspace has already used all activation slots, use <span className='font-medium'>Reset All Activations</span> to revoke old installations and recover access here.
              </p>
            </div>
            <div className='mt-3 flex flex-wrap gap-2'>
              <Button variant='secondary' onClick={startCheckout} disabled={startingCheckout || checkoutBlockedByBillingEmail}>
                {startingCheckout ? 'Redirecting...' : 'Buy / Renew Subscription'}
              </Button>
              <a
                href='https://polar.sh/knowledgebase-ai/portal'
                target='_blank'
                rel='noopener noreferrer'
                className='inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50'
              >
                Access My Purchases
              </a>
              <Button
                variant='secondary'
                onClick={() => validateLicense({ silent: false })}
                disabled={validatingLicense || !licenseStatus.instance_id_configured || !licenseStatus.license_key_configured}
              >
                {validatingLicense ? 'Validating...' : 'Validate Installation'}
              </Button>
              <Button
                variant='secondary'
                onClick={deactivateLicense}
                disabled={
                  deactivatingLicense || !licenseStatus.instance_id_configured || !licenseStatus.license_key_configured
                }
              >
                {deactivatingLicense ? 'Deactivating...' : 'Deactivate This Installation'}
              </Button>
              <Button
                variant='secondary'
                onClick={resetActivations}
                disabled={resettingActivations || (licenseStatus.remote_active_activation_count ?? 0) === 0}
              >
                {resettingActivations ? 'Resetting activations...' : 'Reset All Activations'}
              </Button>
            </div>
            <p className='mt-2 text-[11px] text-slate-500'>
              Use <span className='font-medium'>Access My Purchases</span> to open the secure Polar customer portal in
              a new tab. There you can sign in with this billing email, review your billing history, manage your
              subscription, or cancel it.
            </p>
          </div>
        ) : null}
        {canSaveProvider ? (
          <div className='mt-4 space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600'>
            <div>
              <p className='font-semibold text-slate-700'>OpenAI Setup Help</p>
              <p className='mt-1'>
                If you use OpenAI as runtime provider, create an API key in your OpenAI account and paste it into
                the OpenAI API Key field above.
              </p>
              <a
                href='https://platform.openai.com/api-keys'
                target='_blank'
                rel='noopener noreferrer'
                className='mt-1 inline-block text-brand-700 underline hover:no-underline'
              >
                Create an OpenAI API key
              </a>
            </div>
            <div>
              <p className='font-semibold text-slate-700'>Ollama Integration Help</p>
              <p className='mt-1'>
                Ollama runs locally on your machine (or another reachable host). This app connects to Ollama through
                the Ollama Base URL. When the app runs in Docker and Ollama runs on the host, use
                `http://host.docker.internal:11434`.
              </p>
              <div className='mt-1 flex flex-wrap gap-3'>
                <a
                  href='https://ollama.com/download'
                  target='_blank'
                  rel='noopener noreferrer'
                  className='text-brand-700 underline hover:no-underline'
                >
                  Install Ollama
                </a>
                <a
                  href='https://ollama.com/library'
                  target='_blank'
                  rel='noopener noreferrer'
                  className='text-brand-700 underline hover:no-underline'
                >
                  Browse Ollama models
                </a>
              </div>
            </div>
          </div>
        ) : null}
      </Card>

      <Card>
        <h2 className='text-sm font-semibold'>Service Health</h2>
        {health ? (
          <div className='mt-3 space-y-1 text-sm text-slate-600'>
            <p>Database: {health.db ? 'OK' : 'Down'}</p>
            <p>Redis: {health.redis ? 'OK' : 'Down'}</p>
            <p>LLM Provider: {health.provider.llm}</p>
            <p>Embeddings Provider: {health.provider.embeddings}</p>
            <p>OpenAI Key Configured: {health.provider.openai_api_key_configured ? 'Yes' : 'No'}</p>
            <p>Ollama Reachable: {health.provider.ollama_reachable == null ? 'N/A' : health.provider.ollama_reachable ? 'Yes' : 'No'}</p>
          </div>
        ) : null}
      </Card>

      {canSaveProvider ? (
        <Card>
          <h2 className='text-sm font-semibold'>Support Diagnostics</h2>
          <p className='mt-2 text-xs text-slate-500'>
            Export a bounded ZIP archive of recent API and worker events for support troubleshooting. The archive is
            limited to recent operational logs and excludes secrets and document/chat contents.
          </p>
          {diagnosticsFeedback ? (
            <div className='mt-3'>
              <FeedbackBanner feedback={diagnosticsFeedback} />
            </div>
          ) : null}
          <div className='mt-3'>
            <Button variant='secondary' onClick={exportSupportLogs} disabled={exportingLogs}>
              {exportingLogs ? 'Preparing log export...' : 'Export Support Logs'}
            </Button>
          </div>
        </Card>
      ) : null}

      <Card>
        <h2 className='text-sm font-semibold'>Data Settings</h2>
        {dataSettings ? (
          <div className='mt-3 grid gap-3 md:grid-cols-4'>
            <input
              className='rounded-2xl border border-slate-200 px-3 py-2 text-sm'
              type='number'
              value={dataSettings.retention_days}
              onChange={(e) =>
                setDataSettings((prev) =>
                  prev ? { ...prev, retention_days: Number(e.target.value || 0) } : prev
                )
              }
            />
            <input
              className='rounded-2xl border border-slate-200 px-3 py-2 text-sm'
              type='number'
              value={dataSettings.max_upload_mb}
              onChange={(e) =>
                setDataSettings((prev) =>
                  prev ? { ...prev, max_upload_mb: Number(e.target.value || 0) } : prev
                )
              }
            />
            <Select
              value={dataSettings.email_helper_enabled ? 'enabled' : 'disabled'}
              onChange={(e) =>
                setDataSettings((prev) =>
                  prev ? { ...prev, email_helper_enabled: e.target.value === 'enabled' } : prev
                )
              }
            >
              <option value='enabled'>Email Helper enabled</option>
              <option value='disabled'>Email Helper disabled</option>
            </Select>
            <Button onClick={saveDataSettings} disabled={savingData || !canSaveData}>
              {savingData ? 'Saving...' : 'Save'}
            </Button>
            <p className='text-xs text-slate-500'>Retention days</p>
            <p className='text-xs text-slate-500'>Max upload MB</p>
            <p className='text-xs text-slate-500'>Global Email Helper toggle</p>
          </div>
        ) : null}
      </Card>
        </>
      )}

      {message ? <FeedbackBanner feedback={{ tone: 'info', text: message }} /> : null}
    </div>
  );
}

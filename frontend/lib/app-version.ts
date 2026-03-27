import packageJson from '@/package.json';

const rawAppVersion = (packageJson.version || '').trim();

export const appVersion = rawAppVersion;
export const appReleaseTag = rawAppVersion ? `v${rawAppVersion.replace(/^v/i, '')}` : 'Unknown';

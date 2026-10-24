export function validateEnvironment(values: Record<string, unknown>): Record<string, unknown> {
  const databaseURL = values.DATABASE_URL;
  if (typeof databaseURL !== 'string' || !databaseURL) {
    throw new Error('DATABASE_URL is required');
  }
  const url = new URL(databaseURL);
  if (
    !['postgres:', 'postgresql:'].includes(url.protocol) ||
    !url.hostname ||
    url.pathname === '/'
  ) {
    throw new Error('DATABASE_URL must identify a PostgreSQL database');
  }
  const port = Number(values.PORT ?? 3000);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error('PORT must be an integer between 1 and 65535');
  }
  return { ...values, DATABASE_URL: databaseURL, PORT: port };
}

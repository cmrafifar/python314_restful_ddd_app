import 'dotenv/config';
import { defineConfig } from 'prisma/config';

export default defineConfig({
  schema: 'prisma/schema.prisma',
  migrations: { path: 'prisma/migrations' },
  // Generation/builds do not need database access. Migration commands must supply DATABASE_URL.
  datasource: { url: process.env.DATABASE_URL ?? '' },
});

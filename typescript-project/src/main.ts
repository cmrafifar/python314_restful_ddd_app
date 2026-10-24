import 'reflect-metadata';
import { Logger, ValidationPipe } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NestFactory } from '@nestjs/core';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { AppModule } from './app.module.js';
import { CatalogErrorFilter } from './platform/http/catalog-error.filter.js';
import type { NestExpressApplication } from '@nestjs/platform-express';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create<NestExpressApplication>(AppModule);
  // Express otherwise generates weak ETags, including for transformed PUT and collection responses.
  app.set('etag', false);
  app.disable('x-powered-by');
  app.useGlobalPipes(
    new ValidationPipe({
      transform: true,
      whitelist: true,
      forbidNonWhitelisted: true,
      forbidUnknownValues: true,
    }),
  );
  app.useGlobalFilters(new CatalogErrorFilter());
  app.enableShutdownHooks();
  const config = new DocumentBuilder()
    .setTitle('Bookstore API')
    .setDescription('A bookstore catalog built with NestJS, Prisma, DDD, and hexagonal boundaries.')
    .setVersion('1.0')
    .build();
  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('docs', app, document, { jsonDocumentUrl: '/openapi.json' });
  app
    .getHttpAdapter()
    .getInstance()
    .get('/redoc', (_request, response) => {
      response.type('html').send(`<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Bookstore API — ReDoc</title><style>body{margin:0}</style></head>
<body><redoc spec-url="/openapi.json"></redoc><script src="https://cdn.redoc.ly/redoc/v3.0.1/bundles/redoc.standalone.js"></script></body></html>`);
    });
  await app.listen(app.get(ConfigService).getOrThrow<number>('PORT'), '0.0.0.0');
}

bootstrap().catch((error: unknown) => {
  Logger.error(error, undefined, 'Bootstrap');
  process.exitCode = 1;
});

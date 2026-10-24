import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { BooksModule } from './books/books.module.js';
import { validateEnvironment } from './platform/configuration/environment.js';
import { HealthController } from './health.controller.js';

@Module({
  imports: [ConfigModule.forRoot({ isGlobal: true, validate: validateEnvironment }), BooksModule],
  controllers: [HealthController],
})
export class AppModule {}

import { Module } from '@nestjs/common';
import { BookCatalog } from './application/book-catalog.js';
import { PrismaBookTransactions } from './adapters/persistence/prisma-book-transactions.js';
import { BooksController } from './adapters/http/books.controller.js';
import { PersistenceModule } from '../platform/persistence/persistence.module.js';
import { PrismaService } from '../platform/persistence/prisma.service.js';

@Module({
  imports: [PersistenceModule],
  controllers: [BooksController],
  providers: [
    {
      provide: BookCatalog,
      inject: [PrismaService],
      useFactory: (prisma: PrismaService) => new BookCatalog(new PrismaBookTransactions(prisma)),
    },
  ],
})
export class BooksModule {}

import type { BookRepository, BookTransactions } from '../../application/book-repository.js';
import type { PrismaService } from '../../../platform/persistence/prisma.service.js';
import { PrismaBookRepository } from './prisma-book-repository.js';

export class PrismaBookTransactions implements BookTransactions {
  constructor(private readonly prisma: PrismaService) {}

  async run<T>(work: (books: BookRepository) => Promise<T>): Promise<T> {
    return this.prisma.$transaction((client) => work(new PrismaBookRepository(client)));
  }
}

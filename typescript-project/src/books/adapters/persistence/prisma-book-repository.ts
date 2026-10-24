import { Book } from '../../domain/book.js';
import { ISBN } from '../../domain/isbn.js';
import { InvalidBookError } from '../../domain/errors.js';
import type { BookRepository, BookSelection } from '../../application/book-repository.js';
import { BookAlreadyExistsError, BookVersionConflictError } from '../../application/errors.js';
import { Prisma } from '../../../generated/prisma/client.js';
import type { Book as BookRecord } from '../../../generated/prisma/client.js';

export class PrismaBookRepository implements BookRepository {
  constructor(private readonly client: Prisma.TransactionClient) {}

  async get(id: string): Promise<Book | null> {
    const record = await this.client.book.findUnique({ where: { id } });
    return record ? toDomain(record) : null;
  }

  async getByISBN(isbn: ISBN): Promise<Book | null> {
    const record = await this.client.book.findUnique({ where: { isbn: isbn.value } });
    return record ? toDomain(record) : null;
  }

  async add(book: Book): Promise<void> {
    try {
      await this.client.book.create({
        data: {
          id: book.id,
          isbn: book.isbn.value,
          title: book.title,
          author: book.author,
          version: book.version,
        },
      });
    } catch (error) {
      if (
        error instanceof Prisma.PrismaClientKnownRequestError &&
        error.code === 'P2002' &&
        isISBNConflict(error.meta)
      ) {
        throw new BookAlreadyExistsError('A resource with the supplied ISBN already exists', {
          cause: error,
        });
      }
      throw error;
    }
  }

  async update(book: Book): Promise<Book> {
    const result = await this.client.book.updateMany({
      where: { id: book.id, version: book.version },
      data: { title: book.title, author: book.author, version: { increment: 1 } },
    });
    if (result.count !== 1)
      throw new BookVersionConflictError('The resource changed or was deleted');
    return Book.reconstitute(book.id, book.isbn, book.title, book.author, book.version + 1);
  }

  async delete(book: Book): Promise<void> {
    const result = await this.client.book.deleteMany({
      where: { id: book.id, version: book.version },
    });
    if (result.count !== 1)
      throw new BookVersionConflictError('The resource changed or was deleted');
  }

  async list(selection: BookSelection, limit: number): Promise<Book[]> {
    const order = selection.cursor?.direction === 'previous' ? Prisma.sql`DESC` : Prisma.sql`ASC`;
    const rows = await this.client.$queryRaw<BookRecord[]>(Prisma.sql`
      SELECT id, isbn, title, author, version FROM books
      WHERE ${conditions(selection)} ORDER BY isbn ${order} LIMIT ${limit}
    `);
    return rows.map(toDomain);
  }

  async hasBooks(selection: BookSelection): Promise<boolean> {
    const [row] = await this.client.$queryRaw<{ present: boolean }[]>(Prisma.sql`
      SELECT EXISTS(SELECT 1 FROM books WHERE ${conditions(selection)}) AS present
    `);
    return row?.present ?? false;
  }
}

function conditions(selection: BookSelection): Prisma.Sql {
  const clauses = [Prisma.sql`TRUE`];
  // strpos treats %, _ and backslashes literally. C collation keeps matching case/accent sensitive.
  if (selection.title !== undefined)
    clauses.push(Prisma.sql`strpos(title COLLATE "C", ${selection.title}) > 0`);
  if (selection.author !== undefined)
    clauses.push(Prisma.sql`strpos(author COLLATE "C", ${selection.author}) > 0`);
  if (selection.cursor) {
    const boundary = selection.cursor.isbn.value;
    clauses.push(
      selection.cursor.direction === 'previous'
        ? Prisma.sql`isbn < ${boundary}`
        : Prisma.sql`isbn > ${boundary}`,
    );
  }
  return Prisma.join(clauses, ' AND ');
}

function toDomain(record: BookRecord): Book {
  try {
    return Book.reconstitute(
      record.id,
      new ISBN(record.isbn),
      record.title,
      record.author,
      record.version,
    );
  } catch (error) {
    if (error instanceof InvalidBookError) {
      throw new Error('Invalid persisted book state', { cause: error });
    }
    throw error;
  }
}

function isISBNConflict(meta: Record<string, unknown> | undefined): boolean {
  const target = meta?.target;
  return (
    target === 'uq_books_isbn' ||
    (Array.isArray(target) && target.length === 1 && target[0] === 'isbn')
  );
}

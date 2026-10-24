import { Book, MAX_AUTHOR_LENGTH, MAX_TITLE_LENGTH, normalizeText } from '../domain/book.js';
import { InvalidBookError } from '../domain/errors.js';
import { ISBN } from '../domain/isbn.js';
import type { BookCursor, BookSelection, BookTransactions } from './book-repository.js';
import { BookAlreadyExistsError, BookNotFoundError, BookVersionConflictError } from './errors.js';

export type ExpectedVersions = ReadonlySet<number> | null;
export const MAX_LIST_LIMIT = 100;

export interface BookPage {
  readonly items: readonly Book[];
  readonly hasMore: boolean;
  readonly nextCursor: BookCursor | null;
  readonly previousCursor: BookCursor | null;
}

export class BookCatalog {
  constructor(private readonly transactions: BookTransactions) {}

  async create(command: {
    readonly isbn: string;
    readonly title: string;
    readonly author: string;
  }): Promise<string> {
    const isbn = new ISBN(command.isbn);
    const book = Book.create(isbn, command.title, command.author);
    return this.transactions.run(async (books) => {
      if (await books.getByISBN(isbn)) {
        throw new BookAlreadyExistsError('A resource with the supplied ISBN already exists');
      }
      await books.add(book);
      return book.id;
    });
  }

  async get(id: string): Promise<Book> {
    return this.transactions.run(async (books) => {
      const book = await books.get(id);
      if (!book) throw new BookNotFoundError('Resource not found');
      return book;
    });
  }

  async update(
    id: string,
    details: { readonly title?: string; readonly author?: string },
    versions: ExpectedVersions,
  ): Promise<Book> {
    if (details.title === undefined && details.author === undefined) {
      throw new InvalidBookError('Supply at least one of title or author');
    }
    return this.transactions.run(async (books) => {
      const book = await books.get(id);
      if (!book) throw new BookNotFoundError('Resource not found');
      checkVersion(book, versions);
      book.reviseDetails(details);
      return books.update(book);
    });
  }

  async delete(id: string, versions: ExpectedVersions): Promise<void> {
    await this.transactions.run(async (books) => {
      const book = await books.get(id);
      if (!book) throw new BookNotFoundError('Resource not found');
      checkVersion(book, versions);
      await books.delete(book);
    });
  }

  async list(query: BookSelection & { readonly limit: number }): Promise<BookPage> {
    if (!Number.isInteger(query.limit) || query.limit < 1 || query.limit > MAX_LIST_LIMIT) {
      throw new InvalidBookError(`Limit must be between 1 and ${MAX_LIST_LIMIT}`);
    }
    const selection: BookSelection = {
      ...(query.title === undefined
        ? {}
        : { title: normalizeText(query.title, 'Title', MAX_TITLE_LENGTH) }),
      ...(query.author === undefined
        ? {}
        : { author: normalizeText(query.author, 'Author', MAX_AUTHOR_LENGTH) }),
      ...(query.cursor === undefined ? {} : { cursor: query.cursor }),
    };
    return this.transactions.run(async (books) => {
      const rows = await books.list(selection, query.limit + 1);
      const extra = rows.length > query.limit;
      const items = rows.slice(0, query.limit);
      if (items.length === 0) {
        return { items, hasMore: false, nextCursor: null, previousCursor: null };
      }
      const backward = query.cursor?.direction === 'previous';
      if (backward) items.reverse();
      const first = items.at(0);
      const last = items.at(-1);
      if (!first || !last) throw new Error('Nonempty page required');
      const next: BookCursor = { isbn: last.isbn, direction: 'next' };
      const previous: BookCursor = { isbn: first.isbn, direction: 'previous' };
      const hasNext = backward ? await books.hasBooks({ ...selection, cursor: next }) : extra;
      const hasPrevious = backward
        ? extra
        : query.cursor !== undefined && (await books.hasBooks({ ...selection, cursor: previous }));
      return {
        items,
        hasMore: hasNext,
        nextCursor: hasNext ? next : null,
        previousCursor: hasPrevious ? previous : null,
      };
    });
  }
}

function checkVersion(book: Book, versions: ExpectedVersions): void {
  if (versions !== null && !versions.has(book.version)) {
    throw new BookVersionConflictError(
      'The resource changed; retrieve its current state before retrying',
    );
  }
}

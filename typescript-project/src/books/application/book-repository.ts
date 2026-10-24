import type { Book } from '../domain/book.js';
import type { ISBN } from '../domain/isbn.js';

export interface BookCursor {
  readonly isbn: ISBN;
  readonly direction: 'next' | 'previous';
}

export interface BookSelection {
  readonly title?: string;
  readonly author?: string;
  readonly cursor?: BookCursor;
}

export interface BookRepository {
  get(id: string): Promise<Book | null>;
  getByISBN(isbn: ISBN): Promise<Book | null>;
  add(book: Book): Promise<void>;
  update(book: Book): Promise<Book>;
  delete(book: Book): Promise<void>;
  list(selection: BookSelection, limit: number): Promise<Book[]>;
  hasBooks(selection: BookSelection): Promise<boolean>;
}

export interface BookTransactions {
  run<T>(work: (books: BookRepository) => Promise<T>): Promise<T>;
}

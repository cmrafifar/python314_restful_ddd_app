import { randomUUID } from 'node:crypto';
import { InvalidBookError } from './errors.js';
import type { ISBN } from './isbn.js';

export const MAX_TITLE_LENGTH = 100;
export const MAX_AUTHOR_LENGTH = 80;

export function normalizeText(value: string, label: string, maximum: number): string {
  const normalized = value.trim();
  // Count Unicode code points, matching Python length and PostgreSQL varchar limits.
  const length = Array.from(normalized).length;
  if (length < 1 || length > maximum) {
    throw new InvalidBookError(`${label} must contain between 1 and ${maximum} characters`);
  }
  return normalized;
}

export class Book {
  private currentTitle: string;
  private currentAuthor: string;

  private constructor(
    readonly id: string,
    readonly isbn: ISBN,
    title: string,
    author: string,
    readonly version: number,
  ) {
    this.currentTitle = normalizeText(title, 'Title', MAX_TITLE_LENGTH);
    this.currentAuthor = normalizeText(author, 'Author', MAX_AUTHOR_LENGTH);
  }

  static create(isbn: ISBN, title: string, author: string): Book {
    return new Book(randomUUID(), isbn, title, author, 1);
  }

  static reconstitute(
    id: string,
    isbn: ISBN,
    title: string,
    author: string,
    version: number,
  ): Book {
    if (!Number.isSafeInteger(version) || version < 1) {
      throw new Error('Invalid persisted book version');
    }
    return new Book(id, isbn, title, author, version);
  }

  get title(): string {
    return this.currentTitle;
  }

  get author(): string {
    return this.currentAuthor;
  }

  reviseDetails(details: { readonly title?: string; readonly author?: string }): void {
    const title = normalizeText(details.title ?? this.title, 'Title', MAX_TITLE_LENGTH);
    const author = normalizeText(details.author ?? this.author, 'Author', MAX_AUTHOR_LENGTH);
    // Validate both fields before mutating either one.
    this.currentTitle = title;
    this.currentAuthor = author;
  }
}

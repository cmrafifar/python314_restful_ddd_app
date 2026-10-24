import { BadRequestException } from '@nestjs/common';
import type { BookCursor } from '../../application/book-repository.js';
import { ISBN } from '../../domain/isbn.js';
import { InvalidBookError } from '../../domain/errors.js';

export function encodeCursor(cursor: BookCursor | null): string | null {
  return cursor === null
    ? null
    : Buffer.from(
        JSON.stringify({ v: 1, isbn: cursor.isbn.value, direction: cursor.direction }),
      ).toString('base64url');
}

export function decodeCursor(value: string): BookCursor {
  if (!/^[A-Za-z0-9_-]{1,512}$/.test(value))
    throw new BadRequestException('Invalid pagination cursor');
  let payload: unknown;
  try {
    const bytes = Buffer.from(value, 'base64url');
    if (bytes.toString('base64url') !== value) throw new SyntaxError('Noncanonical cursor');
    payload = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
  } catch {
    throw new BadRequestException('Invalid pagination cursor');
  }
  if (
    typeof payload !== 'object' ||
    payload === null ||
    Array.isArray(payload) ||
    Object.keys(payload).sort().join(',') !== 'direction,isbn,v' ||
    !('v' in payload) ||
    payload.v !== 1 ||
    !('isbn' in payload) ||
    typeof payload.isbn !== 'string' ||
    !('direction' in payload) ||
    (payload.direction !== 'next' && payload.direction !== 'previous')
  ) {
    throw new BadRequestException('Invalid pagination cursor structure');
  }
  try {
    return { isbn: new ISBN(payload.isbn), direction: payload.direction };
  } catch (error) {
    if (error instanceof InvalidBookError)
      throw new BadRequestException('Invalid pagination cursor ISBN');
    throw error;
  }
}

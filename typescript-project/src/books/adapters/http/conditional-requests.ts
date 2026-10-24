import { HttpException } from '@nestjs/common';
import type { ExpectedVersions } from '../../application/book-catalog.js';

const entityTag = '(?:W/)?"[\\x21\\x23-\\x7e\\x80-\\xff]*"';
const ifMatchPattern = new RegExp(
  `^[ \\t]*(?:\\*|${entityTag}(?:[ \\t]*,[ \\t]*${entityTag})*)[ \\t]*$`,
);

export const IF_MATCH_DESCRIPTION =
  'Required. Copy the quoted ETag from GET. Strong tag lists are accepted; weak tags never match. * requires existence but does not protect against stale clients. Missing: 428; malformed: 400; stale: 412.';

export function bookETag(id: string, version: number): string {
  return `"book-${id}-v${version}"`;
}

export function parseIfMatch(id: string, value: string | undefined): ExpectedVersions {
  if (value === undefined) {
    throw new HttpException(
      {
        detail: { code: 'precondition_required', message: "Supply If-Match from the book's ETag" },
      },
      428,
    );
  }
  if (!ifMatchPattern.test(value)) {
    throw new HttpException(
      { detail: { code: 'invalid_if_match', message: 'Invalid If-Match header' } },
      400,
    );
  }
  if (value.trim() === '*') return null;
  const versions = new Set<number>();
  for (const match of value.matchAll(/(W\/)?"([\x21\x23-\x7e\x80-\xff]*)"/g)) {
    const versionMatch = new RegExp(`^book-${id}-v([1-9][0-9]{0,18})$`).exec(match[2] ?? '');
    if (match[1] === undefined && versionMatch?.[1]) {
      const version = Number(versionMatch[1]);
      if (Number.isSafeInteger(version)) versions.add(version);
    }
  }
  return versions;
}

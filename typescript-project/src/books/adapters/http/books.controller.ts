import {
  Body,
  Controller,
  Delete,
  Get,
  Headers,
  HttpCode,
  Param,
  ParseUUIDPipe,
  Patch,
  Post,
  Put,
  Query,
  Res,
} from '@nestjs/common';
import {
  ApiBadRequestResponse,
  ApiConflictResponse,
  ApiCreatedResponse,
  ApiHeader,
  ApiNoContentResponse,
  ApiNotFoundResponse,
  ApiOkResponse,
  ApiOperation,
  ApiParam,
  ApiResponse,
  ApiTags,
  getSchemaPath,
  ApiExtraModels,
} from '@nestjs/swagger';
import type { Response } from 'express';
import { BookCatalog } from '../../application/book-catalog.js';
import type { Book } from '../../domain/book.js';
import { validatedResponse } from '../../../platform/http/validated-response.js';
import {
  BookCreatedResponse,
  BookDetailsResponse,
  BookListQuery,
  BookListResponse,
  CreateBookRequest,
  ErrorResponse,
  PatchBookRequest,
  ReplaceBookRequest,
  ValidationErrorResponse,
} from './book.dto.js';
import { bookETag, IF_MATCH_DESCRIPTION, parseIfMatch } from './conditional-requests.js';
import { decodeCursor, encodeCursor } from './pagination.js';

const etagHeaders = {
  ETag: { description: 'Strong validator to copy into If-Match.', schema: { type: 'string' } },
};

@ApiTags('books')
@ApiExtraModels(ErrorResponse, ValidationErrorResponse)
@ApiBadRequestResponse({
  description: 'Invalid request, cursor, ISBN, or precondition header.',
  schema: {
    oneOf: [
      { $ref: getSchemaPath(ErrorResponse) },
      { $ref: getSchemaPath(ValidationErrorResponse) },
    ],
  },
})
@Controller('api/v1/books')
export class BooksController {
  constructor(private readonly catalog: BookCatalog) {}

  @Post()
  @ApiOperation({ summary: 'Create a catalog record' })
  @ApiCreatedResponse({ type: BookCreatedResponse })
  @ApiConflictResponse({ type: ErrorResponse, description: 'ISBN already exists.' })
  async create(@Body() body: CreateBookRequest): Promise<BookCreatedResponse> {
    return validatedResponse(BookCreatedResponse, { id: await this.catalog.create(body) });
  }

  @Get()
  @ApiOperation({
    summary: 'List matching books',
    description:
      'Case- and accent-sensitive literal title/author filters combine with AND. ISBN ascending order; bounded bidirectional keyset pagination. Preserve filters across requests. Deleted anchors remain usable. No snapshot spans requests; empty pages have no cursors. has_more always describes forward availability. No collection ETag.',
  })
  @ApiOkResponse({ type: BookListResponse })
  async list(@Query() query: BookListQuery): Promise<BookListResponse> {
    const page = await this.catalog.list({
      limit: query.limit,
      ...(query.title === undefined ? {} : { title: query.title }),
      ...(query.author === undefined ? {} : { author: query.author }),
      ...(query.cursor === undefined ? {} : { cursor: decodeCursor(query.cursor) }),
    });
    return validatedResponse(BookListResponse, {
      items: page.items.map(representation),
      has_more: page.hasMore,
      next_cursor: encodeCursor(page.nextCursor),
      previous_cursor: encodeCursor(page.previousCursor),
    });
  }

  @Get(':book_id')
  @ApiParam({ name: 'book_id', format: 'uuid' })
  @ApiOkResponse({ type: BookDetailsResponse, headers: etagHeaders })
  @ApiNotFoundResponse({ type: ErrorResponse })
  async get(
    @Param('book_id', new ParseUUIDPipe()) id: string,
    @Res({ passthrough: true }) response: Response,
  ): Promise<BookDetailsResponse> {
    const book = await this.catalog.get(id);
    const body = await validatedResponse(BookDetailsResponse, representation(book));
    response.setHeader('ETag', bookETag(book.id, book.version));
    return body;
  }

  @Put(':book_id')
  @ApiParam({ name: 'book_id', format: 'uuid' })
  @ApiOperation({
    summary: 'Replace writable details',
    description:
      'Title and author required. ID and ISBN are read-only. Trims outer whitespace. Does not upsert. No ETag on transformed PUT responses; GET for the new validator.',
  })
  @ApiHeader({ name: 'If-Match', required: true, description: IF_MATCH_DESCRIPTION })
  @ApiOkResponse({ type: BookDetailsResponse })
  @ApiNotFoundResponse({ type: ErrorResponse })
  @ApiResponse({
    status: 412,
    type: ErrorResponse,
    description: 'Stale validator or concurrent write.',
  })
  @ApiResponse({
    status: 428,
    type: ErrorResponse,
    description: 'If-Match required.',
    headers: { 'Cache-Control': { schema: { type: 'string', example: 'no-store' } } },
  })
  async replace(
    @Param('book_id', new ParseUUIDPipe()) id: string,
    @Body() body: ReplaceBookRequest,
    @Headers('if-match') condition: string | undefined,
    @Res({ passthrough: true }) response: Response,
  ): Promise<BookDetailsResponse> {
    const versions = this.precondition(id, condition, response);
    return validatedResponse(
      BookDetailsResponse,
      representation(await this.catalog.update(id, body, versions)),
    );
  }

  @Patch(':book_id')
  @ApiParam({ name: 'book_id', format: 'uuid' })
  @ApiOperation({
    summary: 'Change selected details',
    description:
      'Omission preserves fields; explicit null, empty objects, and unknown fields are invalid. This is a field-update object. Successful unchanged writes also advance the version.',
  })
  @ApiHeader({ name: 'If-Match', required: true, description: IF_MATCH_DESCRIPTION })
  @ApiOkResponse({ type: BookDetailsResponse, headers: etagHeaders })
  @ApiNotFoundResponse({ type: ErrorResponse })
  @ApiResponse({
    status: 412,
    type: ErrorResponse,
    description: 'Stale validator or concurrent write.',
  })
  @ApiResponse({
    status: 428,
    type: ErrorResponse,
    description: 'If-Match required.',
    headers: { 'Cache-Control': { schema: { type: 'string', example: 'no-store' } } },
  })
  async patch(
    @Param('book_id', new ParseUUIDPipe()) id: string,
    @Body() body: PatchBookRequest,
    @Headers('if-match') condition: string | undefined,
    @Res({ passthrough: true }) response: Response,
  ): Promise<BookDetailsResponse> {
    const versions = this.precondition(id, condition, response);
    const book = await this.catalog.update(id, body, versions);
    const result = await validatedResponse(BookDetailsResponse, representation(book));
    response.setHeader('ETag', bookETag(book.id, book.version));
    return result;
  }

  @Delete(':book_id')
  @HttpCode(204)
  @ApiParam({ name: 'book_id', format: 'uuid' })
  @ApiOperation({
    summary: 'Permanently delete a book',
    description: 'Frees ISBN for reuse. Empty 204 without ETag. Missing resources return 404.',
  })
  @ApiHeader({ name: 'If-Match', required: true, description: IF_MATCH_DESCRIPTION })
  @ApiNoContentResponse()
  @ApiNotFoundResponse({ type: ErrorResponse })
  @ApiResponse({
    status: 412,
    type: ErrorResponse,
    description: 'Stale validator or concurrent write.',
  })
  @ApiResponse({
    status: 428,
    type: ErrorResponse,
    description: 'If-Match required.',
    headers: { 'Cache-Control': { schema: { type: 'string', example: 'no-store' } } },
  })
  async delete(
    @Param('book_id', new ParseUUIDPipe()) id: string,
    @Headers('if-match') condition: string | undefined,
    @Res({ passthrough: true }) response: Response,
  ): Promise<void> {
    await this.catalog.delete(id, this.precondition(id, condition, response));
  }

  private precondition(id: string, condition: string | undefined, response: Response) {
    if (condition === undefined) response.setHeader('Cache-Control', 'no-store');
    return parseIfMatch(id, condition);
  }
}

function representation(book: Book): BookDetailsResponse {
  return { id: book.id, isbn: book.isbn.value, title: book.title, author: book.author };
}

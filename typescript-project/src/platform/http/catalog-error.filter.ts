import { Catch } from '@nestjs/common';
import type { ArgumentsHost, ExceptionFilter } from '@nestjs/common';
import type { Response } from 'express';
import { InvalidBookError } from '../../books/domain/errors.js';
import {
  BookAlreadyExistsError,
  BookNotFoundError,
  BookVersionConflictError,
} from '../../books/application/errors.js';

@Catch(InvalidBookError, BookAlreadyExistsError, BookNotFoundError, BookVersionConflictError)
export class CatalogErrorFilter implements ExceptionFilter<Error> {
  catch(error: Error, host: ArgumentsHost): void {
    const response = host.switchToHttp().getResponse<Response>();
    const [status, code] =
      error instanceof BookNotFoundError
        ? [404, 'book_not_found']
        : error instanceof BookAlreadyExistsError
          ? [409, 'book_already_exists']
          : error instanceof BookVersionConflictError
            ? [412, 'precondition_failed']
            : [400, 'invalid_book'];
    response.status(status).json({ detail: { code, message: error.message } });
  }
}

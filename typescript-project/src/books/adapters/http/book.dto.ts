import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Transform, Type } from 'class-transformer';
import {
  IsArray,
  IsBoolean,
  IsInt,
  IsString,
  IsUUID,
  Matches,
  Max,
  Min,
  ValidateBy,
  ValidateIf,
  ValidateNested,
} from 'class-validator';
import { MAX_AUTHOR_LENGTH, MAX_TITLE_LENGTH } from '../../domain/book.js';
import { MAX_LIST_LIMIT } from '../../application/book-catalog.js';

function trimText({ value }: { value: unknown }): unknown {
  return typeof value === 'string' ? value.trim() : value;
}

function CodePointLength(maximum: number): PropertyDecorator {
  return ValidateBy({
    name: 'codePointLength',
    validator: {
      validate: (value: unknown) =>
        typeof value === 'string' &&
        Array.from(value).length >= 1 &&
        Array.from(value).length <= maximum,
      defaultMessage: () => `Text must contain between 1 and ${maximum} Unicode code points`,
    },
  });
}

export class ReplaceBookRequest {
  @ApiProperty({ minLength: 1, maxLength: MAX_TITLE_LENGTH })
  @Transform(trimText)
  @IsString()
  @CodePointLength(MAX_TITLE_LENGTH)
  title!: string;

  @ApiProperty({ minLength: 1, maxLength: MAX_AUTHOR_LENGTH })
  @Transform(trimText)
  @IsString()
  @CodePointLength(MAX_AUTHOR_LENGTH)
  author!: string;
}

export class CreateBookRequest extends ReplaceBookRequest {
  @ApiProperty({
    pattern: '^[0-9]{13}$',
    example: '9780132350884',
    description: 'Unformatted ISBN-13 with a valid checksum.',
  })
  @IsString()
  @Matches(/^[0-9]{13}$/)
  isbn!: string;
}

export class PatchBookRequest {
  @ApiPropertyOptional({
    minLength: 1,
    maxLength: MAX_TITLE_LENGTH,
    description: 'Omit to preserve; null is invalid.',
  })
  @ValidateIf((_object: unknown, value: unknown) => value !== undefined)
  @Transform(trimText)
  @IsString()
  @CodePointLength(MAX_TITLE_LENGTH)
  title?: string;

  @ApiPropertyOptional({
    minLength: 1,
    maxLength: MAX_AUTHOR_LENGTH,
    description: 'Omit to preserve; null is invalid.',
  })
  @ValidateIf((_object: unknown, value: unknown) => value !== undefined)
  @Transform(trimText)
  @IsString()
  @CodePointLength(MAX_AUTHOR_LENGTH)
  author?: string;
}

export class BookListQuery {
  @ApiPropertyOptional({
    minLength: 1,
    maxLength: MAX_TITLE_LENGTH,
    description: 'Case- and accent-sensitive literal substring.',
  })
  @ValidateIf((_object: unknown, value: unknown) => value !== undefined)
  @Transform(trimText)
  @IsString()
  @CodePointLength(MAX_TITLE_LENGTH)
  title?: string;

  @ApiPropertyOptional({
    minLength: 1,
    maxLength: MAX_AUTHOR_LENGTH,
    description: 'Case- and accent-sensitive literal substring.',
  })
  @ValidateIf((_object: unknown, value: unknown) => value !== undefined)
  @Transform(trimText)
  @IsString()
  @CodePointLength(MAX_AUTHOR_LENGTH)
  author?: string;

  @ApiPropertyOptional({ default: 20, minimum: 1, maximum: MAX_LIST_LIMIT })
  @Transform(({ value }: { value: unknown }) =>
    typeof value === 'string' && /^[0-9]+$/.test(value) ? Number(value) : value,
  )
  @IsInt()
  @Min(1)
  @Max(MAX_LIST_LIMIT)
  limit = 20;

  @ApiPropertyOptional({
    minLength: 1,
    maxLength: 512,
    description: 'Opaque next/previous cursor. Preserve filters between requests.',
  })
  @ValidateIf((_object: unknown, value: unknown) => value !== undefined)
  @IsString()
  @Matches(/^[A-Za-z0-9_-]{1,512}$/)
  cursor?: string;
}

export class BookCreatedResponse {
  @ApiProperty({ format: 'uuid' })
  @IsUUID()
  id!: string;
}

export class BookDetailsResponse extends BookCreatedResponse {
  @ApiProperty({ pattern: '^[0-9]{13}$' })
  @IsString()
  @Matches(/^[0-9]{13}$/)
  isbn!: string;

  @ApiProperty({ minLength: 1, maxLength: MAX_TITLE_LENGTH })
  @IsString()
  @CodePointLength(MAX_TITLE_LENGTH)
  title!: string;

  @ApiProperty({ minLength: 1, maxLength: MAX_AUTHOR_LENGTH })
  @IsString()
  @CodePointLength(MAX_AUTHOR_LENGTH)
  author!: string;
}

export class BookListResponse {
  @ApiProperty({ type: [BookDetailsResponse] })
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => BookDetailsResponse)
  items!: BookDetailsResponse[];

  @ApiProperty({
    description:
      'Whether a next page exists in ascending ISBN order, including backward navigation.',
  })
  @IsBoolean()
  has_more!: boolean;

  @ApiProperty({ type: String, nullable: true })
  @ValidateIf((_object: unknown, value: unknown) => value !== null)
  @IsString()
  @Matches(/^[A-Za-z0-9_-]{1,512}$/)
  next_cursor!: string | null;

  @ApiProperty({ type: String, nullable: true })
  @ValidateIf((_object: unknown, value: unknown) => value !== null)
  @IsString()
  @Matches(/^[A-Za-z0-9_-]{1,512}$/)
  previous_cursor!: string | null;
}

export class ErrorDetail {
  @ApiProperty()
  code!: string;

  @ApiProperty()
  message!: string;
}

export class ErrorResponse {
  @ApiProperty({ type: ErrorDetail })
  detail!: ErrorDetail;
}

export class ValidationErrorResponse {
  @ApiProperty({ example: 400 })
  statusCode!: number;

  @ApiProperty({ type: [String] })
  message!: string[];

  @ApiProperty({ example: 'Bad Request' })
  error!: string;
}

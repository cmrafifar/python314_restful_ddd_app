import { InternalServerErrorException, Logger } from '@nestjs/common';
import { plainToInstance } from 'class-transformer';
import type { ClassConstructor } from 'class-transformer';
import { validate } from 'class-validator';

export async function validatedResponse<T extends object>(
  type: ClassConstructor<T>,
  value: T,
): Promise<T> {
  const response = plainToInstance(type, value);
  const errors = await validate(response, {
    whitelist: true,
    forbidNonWhitelisted: true,
    forbidUnknownValues: true,
  });
  if (errors.length !== 0) {
    new Logger('ResponseValidation').error(`Invalid outgoing ${type.name} representation`);
    throw new InternalServerErrorException();
  }
  return response;
}

import { Controller, Get } from '@nestjs/common';
import { ApiOkResponse, ApiProperty, ApiTags } from '@nestjs/swagger';
import { IsIn } from 'class-validator';
import { validatedResponse } from './platform/http/validated-response.js';

class HealthResponse {
  @ApiProperty({ enum: ['ok'] })
  @IsIn(['ok'])
  status!: 'ok';
}

@ApiTags('health')
@Controller('health')
export class HealthController {
  @Get()
  @ApiOkResponse({
    type: HealthResponse,
    description: 'Process liveness; does not query the database.',
  })
  async get(): Promise<HealthResponse> {
    return validatedResponse(HealthResponse, { status: 'ok' });
  }
}

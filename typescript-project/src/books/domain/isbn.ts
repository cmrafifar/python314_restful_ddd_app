import { InvalidBookError } from './errors.js';

export class ISBN {
  readonly value: string;

  constructor(value: string) {
    if (!/^[0-9]{13}$/.test(value)) {
      throw new InvalidBookError('ISBN must contain exactly 13 ASCII digits');
    }
    const digits = Array.from(value, Number);
    const checksum = digits
      .slice(0, 12)
      .reduce((sum, digit, i) => sum + digit * (i % 2 ? 3 : 1), 0);
    if ((10 - (checksum % 10)) % 10 !== digits[12]) {
      throw new InvalidBookError('Invalid ISBN checksum');
    }
    this.value = value;
    Object.freeze(this);
  }

  equals(other: ISBN): boolean {
    return this.value === other.value;
  }
}

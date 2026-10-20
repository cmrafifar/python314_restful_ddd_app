from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ISBN:
    value: str

    def __post_init__(self) -> None:
        if len(self.value) != 13 or not self.value.isascii() or not self.value.isdecimal():
            raise ValueError("ISBN must contain exactly 13 ASCII digits")

        digits = [int(char) for char in self.value]

        checksum = sum(
            digit * (1 if index % 2 == 0 else 3) for index, digit in enumerate(digits[:12])
        )

        check_digit = (10 - checksum % 10) % 10

        if check_digit != digits[12]:
            raise ValueError("Invalid ISBN-13 checksum")

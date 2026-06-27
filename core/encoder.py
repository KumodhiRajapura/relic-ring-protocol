def ascii_to_codex(ascii_value: int, codex: int) -> list[int]:
    if codex < 2 or codex > 36:
        raise ValueError(f"Codex must be between 2 and 36, got {codex}")

    if ascii_value == 0:
        return [0]

    digits = []
    value = ascii_value

    while value > 0:
        digits.append(value % codex)
        value //= codex

    return digits[::-1]


def codex_to_ascii(codex_digits: list[int], codex: int) -> int:
    if codex < 2 or codex > 36:
        raise ValueError(f"Codex must be between 2 and 36, got {codex}")

    for digit in codex_digits:
        if digit < 0 or digit >= codex:
            raise ValueError(
                f"Digit {digit} is invalid for codex {codex} "
                f"(must be 0-{codex - 1})"
            )

    ascii_value = 0
    for digit in codex_digits:
        ascii_value = ascii_value * codex + digit

    return ascii_value


def encode_string_to_codex(text: str, codex: int) -> list[list[int]]:
    if codex < 2 or codex > 36:
        raise ValueError(f"Codex must be between 2 and 36, got {codex}")

    return [ascii_to_codex(ord(char), codex) for char in text]


def decode_codex_to_string(codex_data: list[list[int]], codex: int) -> str:
    if codex < 2 or codex > 36:
        raise ValueError(f"Codex must be between 2 and 36, got {codex}")

    return "".join(chr(codex_to_ascii(digits, codex)) for digits in codex_data)


def convert_payload_between_codex(
    payload: list[list[int]],
    source_codex: int,
    target_codex: int
) -> list[list[int]]:
    if source_codex < 2 or source_codex > 36:
        raise ValueError(f"Source codex must be between 2 and 36, got {source_codex}")
    if target_codex < 2 or target_codex > 36:
        raise ValueError(f"Target codex must be between 2 and 36, got {target_codex}")

    if source_codex == target_codex:
        return payload

    ascii_values = [codex_to_ascii(digits, source_codex) for digits in payload]
    return [ascii_to_codex(val, target_codex) for val in ascii_values]


def codex_to_binary_stream(codex_data: list[list[int]], codex: int) -> bytes:
    if codex < 2 or codex > 36:
        raise ValueError(f"Codex must be between 2 and 36, got {codex}")

    binary = bytearray()
    for codex_digits in codex_data:
        for digit in codex_digits:
            if digit < 0 or digit >= codex:
                raise ValueError(f"Digit {digit} out of range for codex {codex}")
            binary.append(digit)

    return bytes(binary)


def binary_stream_to_codex(
    binary_data: bytes,
    codex: int,
    max_digits_per_char: int = 8
) -> list[list[int]]:
    if codex < 2 or codex > 36:
        raise ValueError(f"Codex must be between 2 and 36, got {codex}")

    for byte_val in binary_data:
        if byte_val >= codex:
            raise ValueError(f"Byte value {byte_val} exceeds codex {codex}")

    result = []
    current_char: list[int] = []

    for byte_val in binary_data:
        current_char.append(byte_val)
        if len(current_char) >= max_digits_per_char:
            result.append(current_char)
            current_char = []

    if current_char:
        result.append(current_char)

    return result


def encode_packet_payload(payload_text: str, target_codex: int) -> dict:
    if target_codex < 2 or target_codex > 36:
        raise ValueError(f"Target codex must be between 2 and 36, got {target_codex}")

    ascii_values = [ord(char) for char in payload_text]
    codex_repr = encode_string_to_codex(payload_text, target_codex)
    binary_stream = codex_to_binary_stream(codex_repr, target_codex)

    return {
        "original_text": payload_text,
        "ascii_values": ascii_values,
        "codex": target_codex,
        "codex_representation": codex_repr,
        "binary_stream": binary_stream,
        "encoded_length": len(binary_stream)
    }


def decode_packet_payload(codex_data: list[list[int]], source_codex: int) -> dict:
    if source_codex < 2 or source_codex > 36:
        raise ValueError(f"Source codex must be between 2 and 36, got {source_codex}")

    ascii_values = [codex_to_ascii(digits, source_codex) for digits in codex_data]
    decoded_text = "".join(chr(val) for val in ascii_values)

    return {
        "original_codex": source_codex,
        "codex_representation": codex_data,
        "ascii_values": ascii_values,
        "decoded_text": decoded_text
    }


def is_valid_codex(codex: int) -> bool:
    return 2 <= codex <= 36


def is_valid_codex_digit(digit: int, codex: int) -> bool:
    if not is_valid_codex(codex):
        return False
    return 0 <= digit < codex


def validate_codex_representation(codex_data: list[list[int]], codex: int) -> bool:
    if not is_valid_codex(codex):
        return False
    return all(is_valid_codex_digit(d, codex) for digits in codex_data for d in digits)


def format_codex_representation(codex_data: list[list[int]]) -> str:
    return " ".join(
        "[" + ",".join(str(d) for d in digits) + "]"
        for digits in codex_data
    )


def explain_encoding(text: str, source_codex: int, target_codex: int) -> str:
    lines = [
        f"Encoding '{text}' from codex {source_codex} to {target_codex}",
        "-" * 60
    ]
    for char in text:
        ascii_val = ord(char)
        codex_repr = ascii_to_codex(ascii_val, target_codex)
        lines.append(
            f"Character '{char}' (ASCII {ascii_val}) "
            f"-> Base {target_codex}: {codex_repr}"
        )
    return "\n".join(lines)

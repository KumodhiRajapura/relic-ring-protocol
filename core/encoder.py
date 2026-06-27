#conversion functions for codex representation and ASCII values

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
    
    # Return in correct order (most significant digit first)
    return digits[::-1]


def codex_to_ascii(codex_digits: list[int], codex: int) -> int:
  
    if codex < 2 or codex > 36:
        raise ValueError(f"Codex must be between 2 and 36, got {codex}")
    
    # Validate all digits are within range [0, codex-1]
    for digit in codex_digits:
        if digit < 0 or digit >= codex:
            raise ValueError(
                f"Digit {digit} is invalid for codex {codex} "
                f"(must be 0-{codex-1})"
            )
    
    ascii_value = 0
    for digit in codex_digits:
        ascii_value = ascii_value * codex + digit
    
    return ascii_value

#standard encoding and decoding functions for strings to codex and vice versa

def encode_string_to_codex(text: str, codex: int) -> list[list[int]]:
  
    if codex < 2 or codex > 36:
        raise ValueError(f"Codex must be between 2 and 36, got {codex}")
    
    encoded = []
    for char in text:
        ascii_val = ord(char)
        codex_digits = ascii_to_codex(ascii_val, codex)
        encoded.append(codex_digits)
    
    return encoded


def decode_codex_to_string(codex_data: list[list[int]], codex: int) -> str:

    if codex < 2 or codex > 36:
        raise ValueError(f"Codex must be between 2 and 36, got {codex}")
    
    decoded = []
    for codex_digits in codex_data:
        ascii_val = codex_to_ascii(codex_digits, codex)
        decoded.append(chr(ascii_val))
    
    return "".join(decoded)


#multi-codex conversion function for payloads between planets

def convert_payload_between_codex(
    payload: list[list[int]],
    source_codex: int,
    target_codex: int
) -> list[list[int]]:
   
    if source_codex < 2 or source_codex > 36:
        raise ValueError(f"Source codex must be between 2 and 36, got {source_codex}")
    if target_codex < 2 or target_codex > 36:
        raise ValueError(f"Target codex must be between 2 and 36, got {target_codex}")
    
    # If same codex, no conversion needed
    if source_codex == target_codex:
        return payload
    
    # Step 1: Decode from source codex to ASCII
    ascii_values = []
    for codex_digits in payload:
        ascii_val = codex_to_ascii(codex_digits, source_codex)
        ascii_values.append(ascii_val)
    
    # Step 2: Encode from ASCII to target codex
    target_payload = []
    for ascii_val in ascii_values:
        codex_digits = ascii_to_codex(ascii_val, target_codex)
        target_payload.append(codex_digits)
    
    return target_payload

#binary stream conversion functions for codex representation

def codex_to_binary_stream(codex_data: list[list[int]], codex: int) -> bytes:
  
    if codex < 2 or codex > 36:
        raise ValueError(f"Codex must be between 2 and 36, got {codex}")
    
    binary = bytearray()
    
    for codex_digits in codex_data:
        for digit in codex_digits:
            if digit < 0 or digit >= codex:
                raise ValueError(
                    f"Digit {digit} out of range for codex {codex}"
                )
            binary.append(digit)
    
    return bytes(binary)


def binary_stream_to_codex(binary_data: bytes, codex: int, 
                          max_digits_per_char: int = 8) -> list[list[int]]:

    if codex < 2 or codex > 36:
        raise ValueError(f"Codex must be between 2 and 36, got {codex}")
    
    # Validate all bytes are valid digits in the codex
    for byte_val in binary_data:
        if byte_val >= codex:
            raise ValueError(
                f"Byte value {byte_val} exceeds codex {codex}"
            )

    codex_digits = []
    current_char = []
    
    for byte_val in binary_data:
        current_char.append(byte_val)
  
        if len(current_char) >= max_digits_per_char:
            codex_digits.append(current_char)
            current_char = []
    
    # Add any remaining digits
    if current_char:
        codex_digits.append(current_char)
    
    return codex_digits

#payload encoding and decoding functions for transmission across void
def encode_packet_payload(payload_text: str, target_codex: int) -> dict:

    if target_codex < 2 or target_codex > 36:
        raise ValueError(f"Target codex must be between 2 and 36, got {target_codex}")
    
    # Convert to ASCII
    ascii_values = [ord(char) for char in payload_text]
    
    # Convert to codex
    codex_repr = encode_string_to_codex(payload_text, target_codex)
    
    # Convert to binary stream
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
    
    # Decode codex → ASCII
    ascii_values = []
    for codex_digits in codex_data:
        ascii_val = codex_to_ascii(codex_digits, source_codex)
        ascii_values.append(ascii_val)
    
    # Convert ASCII → text
    decoded_text = "".join(chr(val) for val in ascii_values)
    
    return {
        "original_codex": source_codex,
        "codex_representation": codex_data,
        "ascii_values": ascii_values,
        "decoded_text": decoded_text
    }

#validation functions for codex and digits
def is_valid_codex(codex: int) -> bool:

    return 2 <= codex <= 36


def is_valid_codex_digit(digit: int, codex: int) -> bool:

    if not is_valid_codex(codex):
        return False
    return 0 <= digit < codex


def validate_codex_representation(codex_data: list[list[int]], codex: int) -> bool:

    if not is_valid_codex(codex):
        return False
    
    for codex_digits in codex_data:
        for digit in codex_digits:
            if not is_valid_codex_digit(digit, codex):
                return False
    
    return True


#def format_codex_representation(codex_data: list[list[int]]) -> str:

def format_codex_representation(codex_data: list[list[int]]) -> str:
   
    return " ".join(
        "[" + ",".join(str(d) for d in digits) + "]"
        for digits in codex_data
    )


def explain_encoding(text: str, source_codex: int, target_codex: int) -> str:
   
    output = []
    output.append(f"Encoding '{text}' from codex {source_codex} to {target_codex}")
    output.append("-" * 60)
    
    for i, char in enumerate(text):
        ascii_val = ord(char)
        codex_repr = ascii_to_codex(ascii_val, target_codex)
        output.append(
            f"Character '{char}' (ASCII {ascii_val}) "
            f"→ Base {target_codex}: {codex_repr}"
        )
    
    return "\n".join(output)
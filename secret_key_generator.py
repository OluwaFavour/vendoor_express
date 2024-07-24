import secrets


def generate_secret_key(length: int) -> str:
    """
    Generate a secret key with a specified length.

    ## Arguments

    - length (int): The length of the secret key.

    ## Returns

    - str: The generated secret key.

    ## Example

    ```python
    secret_key = generate_secret_key(32)
    print(secret_key)
    ```
    """
    secret_key = secrets.token_hex(length)
    return secret_key


# Generate a secret key with a length of 32 characters
secret_key = generate_secret_key(32)
print(secret_key)

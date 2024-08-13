import requests
from typing import Optional, Any

from .config import settings


class Paystack:
    """
    A class representing the Paystack API.
    Attributes:
        base_url (str): The base URL of the Paystack API.
        secret_key (str): The secret key used for authentication.
        headers (dict): The headers used for API requests.
    Methods:
        initialize_transaction(amount: int, email: str, reference: str, **kwargs) -> dict:
            Initializes a transaction with the specified amount, email, reference, and optional parameters.
        verify_transaction(reference: str) -> dict:
            Verifies a transaction with the specified reference.
        fetch_transaction(transaction_id: int) -> dict:
            Fetches a transaction with the specified transaction ID.
        charge_authorization(authorization_code: str, email: str, amount: int, reference: str) -> dict:
            Charges an authorization with the specified authorization code, email, amount, and reference.
    """

    def __init__(self):
        self.base_url = "https://api.paystack.co"
        self.secret_key = settings.paystack_secret_key
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def initialize_transaction(
        self, amount: int, email: str, reference: str, **kwargs
    ) -> dict[str, Any]:
        """
        Initializes a transaction with the specified amount, email, reference, and optional keyword arguments.

        Args:
            amount (int): The amount of the transaction.
            email (str): The email address associated with the transaction.
            reference (str): The reference ID for the transaction.
            **kwargs: Additional keyword arguments for the transaction. Valid options include:
                - callback_url (str): The URL to redirect to after the transaction is completed.
                - currency (str): The currency to use for the transaction.

        Returns:
            dict: The JSON response from the API.

        Raises:
            ValueError: If any invalid keyword argument is provided.
            HTTPError: If an error occurs while making the API request.

        """
        possible_extra_kwargs = ["callback_url", "currency", "metadata", "channels"]
        if not all(kwarg in possible_extra_kwargs for kwarg in kwargs):
            raise ValueError("Invalid keyword argument")
        url = f"{self.base_url}/transaction/initialize"
        data = {"amount": amount, "email": email, "reference": reference}
        data.update(kwargs)
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def verify_transaction(self, reference: str) -> dict[str, Any]:
        """
        Verify a transaction using the provided reference.

        Args:
            reference (str): The reference of the transaction to verify.

        Returns:
            dict: A dictionary containing the response from the verification request.

        Raises:
            HTTPError: If an error occurs while making the API request.

        """
        url = f"{self.base_url}/transaction/verify/{reference}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def fetch_transaction(self, transaction_id: int) -> dict[str, Any]:
        """
        Fetches a transaction from the Paystack API.

        Args:
            transaction_id (int): The ID of the transaction to fetch.

        Returns:
            dict: A dictionary containing the transaction details.

        Raises:
            HTTPError: If an error occurs while making the API request.
        """
        url = f"{self.base_url}/transaction/{transaction_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def charge_authorization(
        self,
        authorization_code: str,
        email: str,
        amount: int,
        reference: str,
        channels: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Charges a customer's authorization for a specified amount.

        Args:
            authorization_code (str): The authorization code of the customer.
            email (str): The email address of the customer.
            amount (int): The amount to charge the customer's authorization.
            reference (str): The reference for the transaction.

        Returns:
            dict: The JSON response from the API.

        Raises:
            HTTPError: If an error occurs while making the API request.
        """
        url = f"{self.base_url}/transaction/charge_authorization"
        data = {
            "authorization_code": authorization_code,
            "email": email,
            "amount": amount,
            "reference": reference,
        }
        if channels:
            data["channels"] = channels
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

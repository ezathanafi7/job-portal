from typing import Any

from django.core.management.base import BaseCommand

from apps.accounts.jwt_tokens import generate_rsa_keypair


class Command(BaseCommand):
    help = "Generate an RS256 key pair for signing JWTs, formatted for a .env file."

    def handle(self, *args: Any, **options: Any) -> None:
        private_pem, public_pem = generate_rsa_keypair()

        def one_line(pem: str) -> str:
            # .env values must be on a single line, so replace line breaks with \n
            return pem.strip().replace("\n", "\\n")

        self.stdout.write("# Paste these 2 lines into main-app/.env. Keep the PRIVATE key secret!")
        self.stdout.write(f"JWT_PRIVATE_KEY='{one_line(private_pem)}'")
        self.stdout.write(f"JWT_PUBLIC_KEY='{one_line(public_pem)}'")